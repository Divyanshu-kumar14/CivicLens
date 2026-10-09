"""Agentic trace logger — every state transition, persisted + exportable.

Plan ref: IMPLEMENTATION_PLAN.md Task 2.2.5.
"""
from __future__ import annotations

import json


class TraceLogger:
    def __init__(self, db=None):
        """db: DynamoClient (None -> in-memory, for tests)."""
        self.db = db
        self._memory: dict[str, list[dict]] = {}

    def log_transition(self, ticket_id: str, entry: dict):
        """Append a trace entry to the ticket (Dynamo update or memory)."""
        if self.db is None:
            self._memory.setdefault(ticket_id, []).append(entry)
            return
        ticket = self.db.get_ticket(ticket_id) or {}
        self.db.update_ticket(ticket_id, {"trace": [*ticket.get("trace", []), entry]})

    def get_trace(self, ticket_id: str) -> list[dict]:
        """Full trace history for a ticket."""
        if self.db is None:
            return list(self._memory.get(ticket_id, []))
        return (self.db.get_ticket(ticket_id) or {}).get("trace", [])

    def export_trace_jsonl(self, ticket_id: str) -> str:
        """Trace as JSONL (report/video evidence artifact)."""
        return "\n".join(json.dumps(e, sort_keys=True) for e in self.get_trace(ticket_id))
