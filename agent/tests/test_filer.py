"""Tests for agent/services/filer.py."""
import pytest

from agent.services.filer import TicketFiler
from agent.services.scorer import ScoredCluster
from agent.services.trace import TraceLogger

CONFIG = {"severity": {"auto_file_threshold": 70, "review_threshold": 40}}


class FakeDB:
    def __init__(self):
        self.tickets = {}

    def put_ticket(self, t):
        self.tickets[t["ticket_id"]] = t

    def get_ticket(self, tid):
        return self.tickets.get(tid, {})

    def update_ticket(self, tid, updates):
        self.tickets[tid].update(updates)


class FakeWebhook:
    def __init__(self):
        self.sent = []

    def build_payload(self, ticket):
        return {"ticket_id": ticket["ticket_id"]}

    async def send(self, url, payload):
        self.sent.append((url, payload))
        from agent.services.webhook import WebhookResult

        return WebhookResult(True, 200, 1, 1)


def _scored(severity, n=3):
    return ScoredCluster(cluster_id="c1", det_ids=["d0", "d1", "d2"],
                         centroid=(12.9, 77.5), repeat_count=n,
                         representative_det_id="d0", detections=[],
                         severity=severity, classification="x",
                         signals={"area_norm": 50})


def _filer():
    db, wh, trace = FakeDB(), FakeWebhook(), TraceLogger(None)
    return TicketFiler(CONFIG, db, wh, trace), db, wh, trace


def test_high_severity_files_and_webhooks():
    filer, db, wh, trace = _filer()
    ticket = filer.process_cluster(_scored(82), webhook_url="http://city/hook")
    assert ticket["status"] == "filed"
    assert len(wh.sent) == 1
    assert db.tickets[ticket["ticket_id"]]["status"] == "filed"


def test_low_severity_dismisses_silently():
    filer, db, wh, trace = _filer()
    ticket = filer.process_cluster(_scored(20, n=1))
    assert ticket["status"] == "dismissed"
    assert wh.sent == []


def test_arterial_critical_forces_review():
    filer, db, wh, trace = _filer()
    ticket = filer.process_cluster(_scored(90, n=6), arterial=True)
    assert ticket["status"] == "pending"
    assert wh.sent == []


def test_override_appends_human_trace():
    filer, db, wh, trace = _filer()
    ticket = filer.process_cluster(_scored(50))
    updated = filer.handle_override(ticket["ticket_id"], "dismissed", "false positive")
    assert updated["status"] == "dismissed"
    entries = trace.get_trace(ticket["ticket_id"])
    assert entries[-1]["actor"] == "human"
    assert entries[-1]["reasons"] == ["false positive"]


def test_override_exported_rejected():
    filer, db, wh, trace = _filer()
    ticket = filer.process_cluster(_scored(50))
    db.tickets[ticket["ticket_id"]]["exported"] = True
    with pytest.raises(ValueError, match="exported"):
        filer.handle_override(ticket["ticket_id"], "filed", "x")
