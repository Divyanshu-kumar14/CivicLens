"""Tests for agent/demo_worker.py — synthetic video + GPS, no AWS/torch."""
import numpy as np

from agent.demo_worker import DemoWorker


class FakeDB:
    def __init__(self):
        self.statuses = {}
        self.detections = []
        self.tickets = {}

    def update_job_status(self, jid, status, counts=None):
        self.statuses[jid] = (status, counts or {})

    def put_detections(self, dets):
        self.detections.extend(dets)

    def get_ticket(self, tid):
        return self.tickets.get(tid, {})

    def put_ticket(self, t):
        self.tickets[t["ticket_id"]] = t

    def update_ticket(self, tid, updates):
        # DynamoDB update_item upserts — mirror that here (trace lands before put).
        self.tickets.setdefault(tid, {"ticket_id": tid}).update(updates)


class FakeS3:
    def __init__(self):
        self.crops = {}
        self.files = {}
        self.raw_bucket = "civic-lens-raw"

    def upload_crop(self, data, det_id):
        self.crops[det_id] = data
        return f"s3://crops/{det_id}.jpg"

    def put_file(self, local_path, bucket, key, content_type="application/octet-stream"):
        self.files[key] = local_path
        return f"s3://{bucket}/{key}"


def _synthetic_route(tmp_path, n_frames=12, fps=5):
    """Gray road with a dark pothole ellipse drifting slightly per frame."""
    import cv2

    video = tmp_path / "route.mp4"
    gps = tmp_path / "route.csv"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (320, 240))
    for i in range(n_frames):
        frame = np.full((240, 320, 3), 150, dtype=np.uint8)
        cv2.ellipse(frame, (160 + i, 130), (55, 38), 0, 0, 360, (25, 25, 25), -1)
        writer.write(frame)
    writer.release()
    # ~2.2m spacing per frame (within the 15m dedup eps -> one cluster)
    rows = ["t,lat,lon"] + [f"{i / fps:.2f},{12.97 + i * 0.00002:.6f},77.594600"
                            for i in range(n_frames)]
    gps.write_text("\n".join(rows) + "\n")
    return str(video), str(gps)


def test_demo_worker_completes_job_end_to_end(tmp_path):
    video, gps = _synthetic_route(tmp_path)
    db, s3 = FakeDB(), FakeS3()
    worker = DemoWorker(config={"severity": {}, "dedup": {}}, db=db, s3=s3)
    counts = worker.process_job({"job_id": "j-demo", "video_url": video,
                                 "gps_url": gps})
    assert db.statuses["j-demo"][0] == "completed"
    assert counts["raw"] > 0
    assert counts["clusters"] >= 1
    assert sum(counts[k] for k in ("filed", "review", "dismissed")) == counts["clusters"]
    assert len(s3.crops) == counts["raw"]  # every detection stored a crop
    assert len(db.detections) == counts["raw"]
    # Annotated timelapse uploaded next to the crops.
    assert counts["annotated_url"].startswith("s3://civic-lens-raw/j-demo/")
    assert len(s3.files) == 1


def test_demo_worker_without_gps_uses_fallback(tmp_path):
    video, _ = _synthetic_route(tmp_path)
    db, s3 = FakeDB(), FakeS3()
    worker = DemoWorker(config={"severity": {}, "dedup": {}}, db=db, s3=s3)
    counts = worker.process_job({"job_id": "j-nogps", "video_url": video,
                                 "gps_url": ""})
    assert db.statuses["j-nogps"][0] == "completed"
    assert counts["raw"] > 0


def test_bright_paint_ignored_not_detected(tmp_path):
    """Regression guard for the 1-hole→27-tickets failure: bright markings
    (lane paint) must not become detections; only the dark hole counts."""
    import cv2

    video = tmp_path / "paint.mp4"
    gps = tmp_path / "paint.csv"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"),
                             5, (320, 240))
    for i in range(10):
        frame = np.full((240, 320, 3), 150, dtype=np.uint8)
        cv2.rectangle(frame, (20, 100 + i), (300, 130 + i), (235, 235, 235), -1)
        writer.write(frame)
    writer.release()
    gps.write_text("t,lat,lon\n" + "\n".join(
        f"{i / 5:.1f},12.970000,77.594600" for i in range(10)) + "\n")
    db, s3 = FakeDB(), FakeS3()
    worker = DemoWorker(config={"severity": {}, "dedup": {}}, db=db, s3=s3)
    counts = worker.process_job({"job_id": "j-paint", "video_url": str(video),
                                 "gps_url": str(gps)})
    assert db.statuses["j-paint"][0] == "completed"
    assert counts["raw"] == 0
    assert counts["clusters"] == 0


def test_demo_worker_blurs_crops_before_storage(tmp_path, monkeypatch):
    """Crops pass through PrivacyBlur.process_crop before S3 upload."""
    import vision.blur as blur_mod

    video, gps = _synthetic_route(tmp_path)
    seen = []

    class SpyBlur:
        def __init__(self, config):
            pass

        def process_crop(self, crop):
            seen.append(crop.shape)
            return crop

    monkeypatch.setattr(blur_mod, "PrivacyBlur", SpyBlur)
    db, s3 = FakeDB(), FakeS3()
    worker = DemoWorker(config={"severity": {}, "dedup": {}}, db=db, s3=s3)
    counts = worker.process_job({"job_id": "j-blur", "video_url": video,
                                 "gps_url": gps})
    assert counts["raw"] > 0
    assert len(seen) == counts["raw"]  # every stored crop went through blur


def test_demo_worker_blur_unavailable_still_completes(tmp_path, monkeypatch):
    """Blur init failure degrades to unblurred crops, never a lost job."""
    import vision.blur as blur_mod

    def _boom(config):
        raise RuntimeError("no cv2")

    monkeypatch.setattr(blur_mod, "PrivacyBlur", _boom)
    video, gps = _synthetic_route(tmp_path)
    db, s3 = FakeDB(), FakeS3()
    worker = DemoWorker(config={"severity": {}, "dedup": {}}, db=db, s3=s3)
    counts = worker.process_job({"job_id": "j-noblur", "video_url": video,
                                 "gps_url": gps})
    assert db.statuses["j-noblur"][0] == "completed"
    assert counts["raw"] > 0


def test_demo_worker_bad_video_marks_failed(tmp_path):
    """Unopenable video marks the job failed with the cause, then raises."""
    import pytest

    db, s3 = FakeDB(), FakeS3()
    worker = DemoWorker(config={"severity": {}, "dedup": {}}, db=db, s3=s3)
    with pytest.raises(Exception):
        worker.process_job({"job_id": "j-bad", "video_url": str(tmp_path / "missing.mp4"),
                            "gps_url": ""})
    status, counts = db.statuses["j-bad"]
    assert status == "failed"
    assert counts["error"]


def test_demo_worker_redelivery_skips_completed(tmp_path):
    """A restarted worker re-offered a finished job does not re-file tickets."""
    video, gps = _synthetic_route(tmp_path)

    class DoneDB(FakeDB):
        def get_job(self, jid):
            return {"job_id": jid, "status": "completed",
                    "counts": {"raw": 1, "clusters": 1, "filed": 0,
                               "review": 1, "dismissed": 0, "annotated_url": ""}}

    db, s3 = DoneDB(), FakeS3()
    worker = DemoWorker(config={"severity": {}, "dedup": {}}, db=db, s3=s3)
    counts = worker.process_job({"job_id": "j-redeliver", "video_url": video,
                                 "gps_url": gps})
    assert counts["review"] == 1
    assert s3.crops == {}  # vision never re-ran, nothing re-uploaded
