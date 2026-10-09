"""Committed route suite (replaces the Phase-1 throwaway smoke)."""
from fastapi.testclient import TestClient

import agent.routes.jobs as jobs_mod
from agent.main import app


class FakeDB:
    def __init__(self):
        self.jobs = {}
        self.tickets = {
            "t1": {"ticket_id": "t1", "centroid": [12.9, 77.5], "severity": 80,
                   "status": "pending", "trace": [], "signals": {}, "crop_url": ""},
            "t2": {"ticket_id": "t2", "centroid": [12.8, 77.4], "severity": 30,
                   "status": "filed", "trace": [], "signals": {}, "crop_url": ""},
        }

    def create_job(self, job):
        self.jobs[job["job_id"]] = job
        return job["job_id"]

    def get_job(self, jid):
        return self.jobs.get(jid, {})

    def query_tickets(self, status=None, sort_by="severity"):
        items = [t for t in self.tickets.values() if not status or t["status"] == status]
        if sort_by == "severity":
            items.sort(key=lambda t: t.get("severity", 0), reverse=True)
        return items

    def get_ticket(self, tid):
        return dict(self.tickets.get(tid, {}))

    def update_ticket(self, tid, updates):
        self.tickets[tid].update(updates)


def _client():
    fake = FakeDB()
    app.dependency_overrides[jobs_mod.get_db] = lambda: fake
    jobs_mod.send_job_message = lambda job: None
    return TestClient(app), fake


def test_health():
    c, _ = _client()
    assert c.get("/health").json() == {"status": "ok", "service": "civiclens-agent"}


def test_job_lifecycle():
    c, _ = _client()
    r = c.post("/jobs", json={"video_url": "http://x/v.mp4", "gps_url": "http://x/g.csv"})
    assert r.status_code == 201
    jid = r.json()["job_id"]
    assert c.get(f"/jobs/{jid}").json()["status"] == "queued"
    assert c.get("/jobs/missing").status_code == 404


def test_ticket_list_sort_and_filter():
    c, _ = _client()
    all_t = c.get("/tickets").json()
    assert [t["ticket_id"] for t in all_t] == ["t1", "t2"]  # severity desc
    assert [t["ticket_id"] for t in c.get("/tickets", params={"status": "filed"}).json()] == ["t2"]
    assert c.get("/tickets", params={"sort": "bogus"}).status_code == 422


def test_override_flow_and_guards():
    c, fake = _client()
    r = c.post("/tickets/t1/override", json={"to": "filed", "reason": "confirmed"})
    assert r.json()["status"] == "filed"
    assert fake.tickets["t1"]["trace"][0]["actor"] == "human"
    assert c.post("/tickets/nope/override", json={"to": "filed"}).status_code == 404
    fake.tickets["t1"]["exported"] = True
    assert c.post("/tickets/t1/override", json={"to": "dismissed"}).status_code == 409


def test_export_csv_and_webhook_shape():
    c, _ = _client()
    r = c.get("/export.csv", params={"status": "filed"})
    assert r.status_code == 200
    assert r.text.splitlines()[0] == "ticket_id,lat,lon,severity,status,crop_url,video_url,t,RoadName"
    assert "t2" in r.text
    r = c.post("/webhooks/test", json={"url": "http://127.0.0.1:9/nope"})
    assert r.json()["ok"] is False
