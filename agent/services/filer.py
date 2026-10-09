"""Agentic file / queue / dismiss loop + human override path.

Plan ref: IMPLEMENTATION_PLAN.md Task 2.2.3.
Every transition is trace-logged (agent or human actor) — the evidence base
for the Agentic Vision award.
"""
from __future__ import annotations

import logging
import time
import uuid

from agent.services.scorer import ScoredCluster

log = logging.getLogger("civiclens.filer")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class TicketFiler:
    def __init__(self, config: dict, db=None, webhook=None, trace=None):
        """db: DynamoClient, webhook: WebhookService, trace: TraceLogger (injectable)."""
        sev = config.get("severity", {})
        self.auto_file_threshold = sev.get("auto_file_threshold", 70)
        self.review_threshold = sev.get("review_threshold", 40)
        self.db = db
        self.webhook = webhook
        self.trace = trace

    def _store(self, ticket: dict) -> dict:
        if self.db is not None:
            self.db.put_ticket(ticket)
        return ticket

    def _log(self, ticket_id: str, from_status: str, to_status: str,
             reasons: list, signals: dict, actor: str = "agent"):
        entry = {"ts": _now(), "actor": actor, "from_status": from_status,
                 "to_status": to_status, "reasons": reasons, "signals": signals}
        if self.trace is not None:
            self.trace.log_transition(ticket_id, entry)
            return None  # persisted via TraceLogger
        return entry  # caller embeds (no trace backend, e.g. tests)

    def process_cluster(self, scored: ScoredCluster, arterial: bool = False,
                        webhook_url: str | None = None) -> dict:
        """PERCEIVE -> DECIDE -> ACT -> STORE. Returns the ticket dict."""
        log.info("cluster %s: severity=%s repeats=%s", scored.cluster_id,
                 scored.severity, scored.repeat_count)

        # DECIDE
        if scored.severity >= self.auto_file_threshold and not (
                scored.severity >= 85 and arterial):
            action, status = "file", "filed"
        elif scored.severity >= 85 and arterial:
            # High-cost arterial repair: force human approval.
            action, status = "review", "pending"
        elif scored.severity >= self.review_threshold:
            action, status = "review", "pending"
        else:
            action, status = "dismiss", "dismissed"

        # ACT
        ticket = {
            "ticket_id": f"t_{uuid.uuid4().hex[:12]}",
            "hole_label": "",
            "det_ids": scored.det_ids,
            "centroid": list(scored.centroid),
            "repeat_count": scored.repeat_count,
            "severity": scored.severity,
            "status": status,
            "signals": scored.signals,
            "trace": [],
            "created_at": _now(),
            "updated_at": _now(),
        }
        reason = {"file": f"severity {scored.severity} >= {self.auto_file_threshold}",
                  "review": "human review required",
                  "dismiss": "low_severity"}[action]
        entry = self._log(ticket["ticket_id"], "new", status, [reason],
                          scored.signals)
        if entry is not None:
            ticket["trace"].append(entry)

        if action == "file" and self.webhook is not None and webhook_url:
            import asyncio

            try:
                asyncio.run(self.webhook.send(webhook_url,
                                              self.webhook.build_payload(ticket)))
            except Exception as exc:  # dead-letter, never lose the ticket
                log.error("webhook failed for %s: %s", ticket["ticket_id"], exc)

        # STORE
        return self._store(ticket)

    def handle_override(self, ticket_id: str, to_status: str, reason: str,
                        webhook_url: str | None = None) -> dict:
        """Human override: validate -> update -> (re-fire webhook) -> trace."""
        if self.db is None:
            raise RuntimeError("handle_override needs a db backend")
        ticket = self.db.get_ticket(ticket_id)
        if not ticket:
            raise KeyError(f"ticket not found: {ticket_id}")
        if ticket.get("exported"):
            raise ValueError("ticket already exported")
        entry = {"ts": _now(), "actor": "human", "from_status": ticket.get("status", ""),
                 "to_status": to_status, "reasons": [reason] if reason else [],
                 "signals": ticket.get("signals", {})}
        if self.trace is not None:
            self.trace.log_transition(ticket_id, entry)
            trace = ticket.get("trace", [])
        else:
            trace = [*ticket.get("trace", []), entry]
        if to_status == "filed" and self.webhook is not None and webhook_url:
            import asyncio

            try:
                asyncio.run(self.webhook.send(webhook_url,
                                              self.webhook.build_payload(ticket)))
            except Exception as exc:
                log.error("override webhook failed for %s: %s", ticket_id, exc)
        updates = {"status": to_status, "trace": trace, "updated_at": _now()}
        self.db.update_ticket(ticket_id, updates)
        return {**ticket, **updates}
