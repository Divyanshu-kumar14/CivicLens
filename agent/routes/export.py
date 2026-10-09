"""Export + webhook test: GET /export.csv, POST /webhooks/test.

Plan ref: IMPLEMENTATION_PLAN.md Task 1.4.4.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import logging
import os
import time
import urllib.request

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.db.dynamo import DynamoClient
from agent.routes.jobs import get_db
from agent.routes.tickets import presign_crop

router = APIRouter()
log = logging.getLogger("civiclens.export")

EXPORT_COLUMNS = ["ticket_id", "lat", "lon", "severity", "status", "crop_url", "video_url", "t", "RoadName"]


class WebhookTestRequest(BaseModel):
    url: str


def _ticket_row(ticket: dict) -> list:
    centroid = ticket.get("centroid", [0.0, 0.0])
    return [
        ticket.get("ticket_id", ""),
        centroid[0] if len(centroid) > 0 else "",
        centroid[1] if len(centroid) > 1 else "",
        ticket.get("severity", ""),
        ticket.get("status", ""),
        ticket.get("crop_url", ""),
        ticket.get("video_url", ""),
        ticket.get("t", ""),
        ticket.get("ward", ""),
    ]


@router.get("/export.csv")
def export_csv(
    status: str = Query(default="filed"),
    db: DynamoClient = Depends(get_db),
):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXPORT_COLUMNS)
    for ticket in db.query_tickets(status=status, sort_by="severity"):
        writer.writerow(_ticket_row(presign_crop(ticket)))
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tickets-{status}.csv"},
    )


def _sign(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


@router.post("/webhooks/test")
def test_webhook(payload: WebhookTestRequest) -> dict:
    body = json.dumps({
        "event": "ticket.filed",
        "ticket_id": "t_test",
        "lat": 12.9716,
        "lon": 77.5946,
        "severity": 78,
        "status": "filed",
        "crop_url": "https://example.invalid/crop.jpg",
        "advisory": "verify on site",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }).encode()
    secret = os.getenv("WEBHOOK_SECRET", "changeme")
    req = urllib.request.Request(
        payload.url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-CivicLens-Signature": _sign(body, secret),
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            latency_ms = int((time.monotonic() - started) * 1000)
            return {"ok": 200 <= resp.status < 300, "latency_ms": latency_ms, "status_code": resp.status}
    except Exception as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        log.warning("webhook test to %s failed: %s", payload.url, exc)
        return {"ok": False, "latency_ms": latency_ms, "status_code": 0}
