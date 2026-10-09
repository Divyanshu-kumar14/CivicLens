"""Tests for agent/worker.py — injected fakes, local file URIs, no AWS."""
from vision.detector import Detection
from agent.worker import BatchWorker


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
        self.tickets[tid].update(updates)


class FakeS3:
    def __init__(self):
        self.crops = {}

    def download_file(self, bucket, key, local):
        raise AssertionError("should use local paths in this test")

    def upload_crop(self, data, det_id):
        self.crops[det_id] = data
        return f"s3://crops/{det_id}.jpg"


class FakePipeline:
    def __init__(self, crop_path):
        self.crop_path = crop_path

    def process_video(self, video, gps, job_id):
        from vision.pipeline import ProcessingResult

        det = Detection(x=0, y=0, w=30, h=30, conf=0.9, frame_idx=0,
                        timestamp_sec=1.0, lat=12.9, lon=77.5,
                        crop_path=self.crop_path)
        try:
            import numpy as np

            det.embedding = np.ones(4, dtype=float)
        except ImportError:
            det.embedding = [1.0, 1.0, 1.0, 1.0]
        return ProcessingResult(job_id=job_id, detections=[det, det],
                                processed_frames=2)


def test_process_job_end_to_end(tmp_path):
    video = tmp_path / "v.mp4"
    gps = tmp_path / "g.csv"
    video.write_bytes(b"fake")
    gps.write_text("t,lat,lon\n0,12.9,77.5\n")
    crop = tmp_path / "crop.jpg"
    crop.write_bytes(b"fake-jpg")

    db, s3 = FakeDB(), FakeS3()
    cluster = {"cid": 1}
    made = {}

    class FakeClusterer:
        def cluster_detections(self, dets):
            assert len(dets) == 2
            return [cluster]

    class FakeScorer:
        def score_cluster(self, c):
            return {"scored": True}

    class FakeFiler:
        def process_cluster(self, scored, webhook_url=None):
            made["webhook"] = webhook_url
            return {"ticket_id": "t1", "status": "filed"}

    worker = BatchWorker(config={"severity": {}}, db=db, s3=s3,
                         pipeline=FakePipeline(str(crop)),
                         clusterer=FakeClusterer(), scorer=FakeScorer(),
                         filer=FakeFiler(), webhook_url="http://city/hook")
    counts = worker.process_job({"job_id": "j1", "video_url": str(video),
                                 "gps_url": str(gps)})
    assert counts == {"raw": 2, "clusters": 1, "filed": 1, "review": 0, "dismissed": 0}
    assert db.statuses["j1"][0] == "completed"
    assert len(db.detections) == 2
    assert made["webhook"] == "http://city/hook"
