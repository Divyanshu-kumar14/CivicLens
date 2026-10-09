"""Job intake: POST /jobs, GET /jobs/{job_id}.

Plan ref: IMPLEMENTATION_PLAN.md Task 1.4.2.
AWS clients are lazy so the app imports without boto3; override `get_db`
/ monkeypatch `send_job_message` in tests.
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException

from agent.db.dynamo import DynamoClient
from agent.models.job import JobCreate

router = APIRouter()
log = logging.getLogger("civiclens.jobs")

MAX_VIDEO_BYTES = 2 * 1024**3  # 2GB intake limit


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


_db: DynamoClient | None = None


def get_db() -> DynamoClient:
    global _db
    if _db is None:
        _db = DynamoClient()
    return _db


def remote_size_ok(url: str) -> bool:
    """Best-effort Content-Length check. Fail-open (True) when unknown."""
    try:
        req = Request(url, method="HEAD")
        with urlopen(req, timeout=5) as resp:
            length = resp.headers.get("Content-Length")
            return length is None or int(length) <= MAX_VIDEO_BYTES
    except Exception as exc:  # unknown size — don't block queueing
        log.warning("size check skipped for %s: %s", url, exc)
        return True


def send_job_message(job: dict) -> None:
    """Enqueue job for the vision worker via SQS."""
    try:
        import boto3
        import json
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="boto3 not installed") from exc
    queue_url = os.getenv("SQS_QUEUE_URL", "")
    if not queue_url:
        raise HTTPException(status_code=500, detail="SQS_QUEUE_URL not configured")
    sqs = boto3.client(
        "sqs",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
    )
    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(job))


@router.post("", status_code=201)
def create_job(payload: JobCreate, db: DynamoClient = Depends(get_db)) -> dict:
    if not remote_size_ok(payload.video_url):
        raise HTTPException(status_code=413, detail="Video exceeds 2GB limit")
    job = {
        "job_id": uuid.uuid4().hex,
        "video_url": payload.video_url,
        "gps_url": payload.gps_url,
        "ward": payload.ward,
        "status": "queued",
        "progress_pct": 0.0,
        "counts": {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    db.create_job(job)
    try:
        send_job_message(job)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"queue send failed: {exc}") from exc
    return {"job_id": job["job_id"], "status": "queued"}


@router.get("/{job_id}")
def get_job(job_id: str, db: DynamoClient = Depends(get_db)) -> dict:
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job
