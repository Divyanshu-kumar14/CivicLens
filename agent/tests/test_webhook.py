"""Tests for agent/services/webhook.py + trace.py."""
import asyncio
import hashlib
import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from agent.services.trace import TraceLogger
from agent.services.webhook import WebhookService


def test_build_payload_shape():
    svc = WebhookService({})
    p = svc.build_payload({"ticket_id": "t1", "centroid": [12.9, 77.5],
                           "severity": 78, "status": "filed", "crop_url": "s3://b/k"})
    assert p["event"] == "ticket.filed" and p["advisory"] == "verify on site"
    assert (p["lat"], p["lon"]) == (12.9, 77.5)


def test_sign_is_deterministic_hmac():
    svc = WebhookService({})
    payload = {"ticket_id": "t1", "severity": 1}
    expected = hmac.new(b"changeme", json.dumps(payload, sort_keys=True).encode(),
                        hashlib.sha256).hexdigest()
    assert svc.sign_payload(payload) == expected
    assert len(expected) == 64


def test_send_success_against_local_server():
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received["sig"] = self.headers.get("X-CivicLens-Signature")
            received["len"] = int(self.headers.get("Content-Length", 0))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        svc = WebhookService({})
        res = asyncio.run(svc.send(f"http://127.0.0.1:{server.server_port}/hook",
                                   {"ticket_id": "t1"}))
    finally:
        server.shutdown()
    assert res.ok and res.status_code == 200 and res.attempts == 1
    assert received["sig"] and received["len"] > 0


def test_send_dead_letters_after_retries(monkeypatch):
    import agent.services.webhook as webhook_mod

    monkeypatch.setattr(webhook_mod, "RETRY_BACKOFF_S", (0, 0, 0))
    svc = WebhookService({})
    res = asyncio.run(svc.send("http://127.0.0.1:9/nope", {"ticket_id": "t9"}))
    assert not res.ok and res.attempts == 4 and res.status_code == 0


def test_trace_memory_roundtrip_and_jsonl():
    trace = TraceLogger(None)
    trace.log_transition("t1", {"ts": "x", "actor": "agent", "from_status": "new",
                                "to_status": "pending", "reasons": ["r"], "signals": {}})
    assert len(trace.get_trace("t1")) == 1
    line = trace.export_trace_jsonl("t1")
    assert json.loads(line)["actor"] == "agent"
