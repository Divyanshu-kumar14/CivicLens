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

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from agent.db.dynamo import DynamoClient
from agent.db.s3 import S3Client
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


_s3: S3Client | None = None


def get_s3() -> S3Client:
    global _s3
    if _s3 is None:
        _s3 = S3Client()
    return _s3


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
    return _enqueue(db, payload.video_url, payload.gps_url, payload.ward)


VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv"}
GPS_EXTS = {".csv", ".srt"}


def _safe_upload_name(upload: UploadFile, allowed: set[str], field: str) -> str:
    """Task 3.1.3: strip paths, allowlist extensions, reject the rest (413/422)."""
    name = (upload.filename or "").split("/")[-1].split("\\")[-1].strip()
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if not name or ext not in allowed:
        raise HTTPException(status_code=422, detail=f"{field}: need one of {sorted(allowed)}")
    if not all(c.isalnum() or c in "._-" for c in name):
        raise HTTPException(status_code=422, detail=f"{field}: unsafe filename")
    return name


@router.post("/upload", status_code=201)
def upload_job(
    video: UploadFile = File(...),
    gps: UploadFile | None = File(default=None),
    ward: str = Form(default="ward-12-demo"),
    db: DynamoClient = Depends(get_db),
    s3: S3Client = Depends(get_s3),
) -> dict:
    """Multipart intake for the web UploadZone: files -> S3 raw -> queued job."""
    import shutil
    import tempfile

    _safe_upload_name(video, VIDEO_EXTS, "video")
    if gps is not None and gps.filename:
        _safe_upload_name(gps, GPS_EXTS, "gps")
    job_id = uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix=f"cl-upload-{job_id}-") as tmp:
        video_local = f"{tmp}/video.mp4"
        with open(video_local, "wb") as fh:
            shutil.copyfileobj(video.file, fh)
        if os.path.getsize(video_local) > MAX_VIDEO_BYTES:
            raise HTTPException(status_code=413, detail="Video exceeds 2GB limit")
        video_url = s3.upload_video(video_local, job_id)
        gps_url = ""
        if gps is not None:
            gps_local = f"{tmp}/gps.csv"
            with open(gps_local, "wb") as fh:
                shutil.copyfileobj(gps.file, fh)
            gps_url = s3.upload_gps(gps_local, job_id)
    return _enqueue(db, video_url, gps_url, ward, job_id=job_id)


def _enqueue(db: DynamoClient, video_url: str, gps_url: str, ward: str,
             job_id: str | None = None) -> dict:
    job = {
        "job_id": job_id or uuid.uuid4().hex,
        "video_url": video_url,
        "gps_url": gps_url,
        "ward": ward,
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
