"""Ticket read + human override: GET /tickets, GET /tickets/{id}, POST override.

Plan ref: IMPLEMENTATION_PLAN.md Task 1.4.3.
Phase 2 adds webhook re-fire on override-to-filed (Task 2.2.3) — hook noted.
"""
from __future__ import annotations

import logging
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from agent.db.dynamo import DynamoClient
from agent.routes.jobs import get_db
from agent.services.cache import get_cache

router = APIRouter()
log = logging.getLogger("civiclens.tickets")

LIST_TTL_S = 5.0  # Task 3.1.4: ticket-list response cache
PRESIGN_TTL_S = 300.0  # Task 3.1.4: presigned-URL cache (URLs live 15 min)


class OverrideRequest(BaseModel):
    to: Literal["filed", "pending", "dismissed"]
    reason: str = ""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def presign_crop(ticket: dict) -> dict:
    """Attach a fresh presigned crop URL; fail-open to the stored URL."""
    url = ticket.get("crop_url", "")
    if not url or not url.startswith("s3://"):
        return ticket
    cached = get_cache().get(("presign", url))
    if cached is not None:
        return {**ticket, "crop_url": cached}
    try:
        from agent.db.s3 import S3Client

        bucket, _, key = url[5:].partition("/")
        fresh = S3Client().get_presigned_url(bucket, key)
        get_cache().set(("presign", url), fresh, ttl_s=PRESIGN_TTL_S)
        ticket = {**ticket, "crop_url": fresh}
    except Exception as exc:
        log.warning("presign failed for %s: %s", url, exc)
    return ticket


@router.get("")
def list_tickets(
    status: str | None = Query(default=None, description="filed|pending|dismissed"),
    sort: Literal["severity", "timestamp"] = Query(default="severity"),
    db: DynamoClient = Depends(get_db),
) -> list[dict]:
    key = ("tickets", status, sort)
    cached = get_cache().get(key)
    if cached is not None:
        return cached
    result = [presign_crop(t) for t in db.query_tickets(status=status, sort_by=sort)]
    get_cache().set(key, result, ttl_s=LIST_TTL_S)
    return result


@router.get("/{ticket_id}")
def get_ticket(ticket_id: str, db: DynamoClient = Depends(get_db)) -> dict:
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
    return presign_crop(ticket)


@router.post("/{ticket_id}/override")
def override_ticket(
    ticket_id: str, payload: OverrideRequest, db: DynamoClient = Depends(get_db)
) -> dict:
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
    if ticket.get("exported"):
        raise HTTPException(status_code=409, detail="ticket already exported")
    entry = {
        "ts": _now(),
        "actor": "human",
        "from_status": ticket.get("status", ""),
        "to_status": payload.to,
        "reasons": [payload.reason] if payload.reason else [],
        "signals": ticket.get("signals", {}),
    }
    # Phase 2 (Task 2.2.3): if overriding to "filed", re-fire webhook here.
    updates = {
        "status": payload.to,
        "trace": [*ticket.get("trace", []), entry],
        "updated_at": _now(),
    }
    db.update_ticket(ticket_id, updates)
    return {**ticket, **updates}
