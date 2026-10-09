"""SQS batch worker: jobs -> vision -> dedup/score/file -> tickets.

Plan ref: IMPLEMENTATION_PLAN.md Task 2.2.6.
All AWS/vision deps are injectable so process_job is unit-testable.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time

log = logging.getLogger("civiclens.worker")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class BatchWorker:
    def __init__(self, config: dict | None = None, db=None, s3=None, sqs=None,
                 pipeline=None, clusterer=None, scorer=None, filer=None,
                 webhook_url: str | None = None):
        """Init from injected deps or build live ones (lazy boto3/vision)."""
        from agent.config import load_agent_config

        self.config = config or load_agent_config()
        self.db = db or self._build_db()
        self.s3 = s3 or self._build_s3()
        self.sqs = sqs  # built lazily in poll_and_process (process_job needs none)
        self.queue_url = os.getenv("SQS_QUEUE_URL", "")
        self.pipeline = pipeline  # built per-job (needs output isolation)
        self.clusterer = clusterer
        self.scorer = scorer
        self.filer = filer
        self.webhook_url = webhook_url or os.getenv("CITY_WEBHOOK_URL")

    @staticmethod
    def _build_db():
        from agent.db.dynamo import DynamoClient

        return DynamoClient()

    @staticmethod
    def _build_s3():
        from agent.db.s3 import S3Client

        return S3Client()

    @staticmethod
    def _build_sqs():
        import boto3

        return boto3.client(
            "sqs",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        )

    def _services(self):
        from agent.services.cluster import DeduplicatorService
        from agent.services.filer import TicketFiler
        from agent.services.scorer import SeverityScorer
        from agent.services.trace import TraceLogger
        from agent.services.webhook import WebhookService

        trace, webhook = TraceLogger(self.db), WebhookService(self.config)
        return (self.clusterer or DeduplicatorService(self.config),
                self.scorer or SeverityScorer(self.config),
                self.filer or TicketFiler(self.config, self.db, webhook, trace))

    def poll_and_process(self, max_messages: int = 1, wait_s: int = 20):
        """Main loop: receive -> process -> delete (failure marks job failed)."""
        if self.sqs is None:
            self.sqs = self._build_sqs()
        while True:
            resp = self.sqs.receive_message(QueueUrl=self.queue_url,
                                            MaxNumberOfMessages=max_messages,
                                            WaitTimeSeconds=wait_s)
            for msg in resp.get("Messages", []):
                job = json.loads(msg["Body"])
                try:
                    self.process_job(job)
                except Exception as exc:
                    log.exception("job %s failed", job.get("job_id"))
                    self.db.update_job_status(job.get("job_id", ""), "failed",
                                              {"error": str(exc)})
                finally:
                    self.sqs.delete_message(QueueUrl=self.queue_url,
                                            ReceiptHandle=msg["ReceiptHandle"])

    def process_job(self, job: dict) -> dict:
        """processing -> download -> vision -> store -> agent loop -> completed."""
        from vision.pipeline import VisionPipeline

        job_id = job["job_id"]
        self.db.update_job_status(job_id, "processing")
        clusterer, scorer, filer = self._services()

        with tempfile.TemporaryDirectory(prefix=f"cl-{job_id}-") as tmp:
            video_local = os.path.join(tmp, "video.mp4")
            gps_local = os.path.join(tmp, "gps.csv")
            self._download(job["video_url"], video_local)
            self._download(job["gps_url"], gps_local)

            pipeline = self.pipeline or VisionPipeline(output_dir=os.path.join(tmp, "crops"))
            result = pipeline.process_video(video_local, gps_local, job_id)

            det_dicts = self._store_detections(job_id, result.detections, tmp)
            clusters = clusterer.cluster_detections(det_dicts)
            counts = {"raw": len(det_dicts), "clusters": len(clusters),
                      "filed": 0, "review": 0, "dismissed": 0}
            for cluster in clusters:
                ticket = filer.process_cluster(scorer.score_cluster(cluster),
                                               webhook_url=self.webhook_url)
                counts[{"filed": "filed", "pending": "review",
                        "dismissed": "dismissed"}[ticket["status"]]] += 1

        self.db.update_job_status(job_id, "completed", counts)
        log.info("job %s completed: %s", job_id, counts)
        return counts

    @staticmethod
    def _split_s3_uri(uri: str) -> tuple[str, str]:
        assert uri.startswith("s3://"), f"not an S3 URI: {uri}"
        bucket, _, key = uri[5:].partition("/")
        return bucket, key

    def _download(self, uri: str, local_path: str):
        if uri.startswith("s3://"):
            bucket, key = self._split_s3_uri(uri)
            self.s3.download_file(bucket, key, local_path)
        else:  # http(s) or local path (dev/test)
            import shutil
            import urllib.request

            if uri.startswith(("http://", "https://")):
                urllib.request.urlretrieve(uri, local_path)
            else:
                shutil.copyfile(uri, local_path)

    def _store_detections(self, job_id: str, detections, tmp: str) -> list[dict]:
        """Upload crops + persist detection rows. Returns cluster-ready dicts."""
        import numpy as np

        rows = []
        for det in detections:
            crop_url = ""
            if det.crop_path and os.path.exists(det.crop_path):
                with open(det.crop_path, "rb") as fh:
                    crop_url = self.s3.upload_crop(fh.read(), det.det_id)
            emb = det.embedding.tolist() if isinstance(det.embedding, np.ndarray) else None
            rows.append({"det_id": det.det_id, "job_id": job_id, "t": det.timestamp_sec,
                         "lat": det.lat, "lon": det.lon, "cls": det.cls,
                         "conf": det.conf, "box": [det.x, det.y, det.w, det.h],
                         "emb_url": "", "crop_url": crop_url, "_embedding": emb,
                         "embedding": emb})
        self.db.put_detections([{k: v for k, v in r.items() if not k.startswith("_")}
                                for r in rows])
        return rows
