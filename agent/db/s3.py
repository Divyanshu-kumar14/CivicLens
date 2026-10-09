"""S3 wrapper: video/GPS upload, crop storage, presigned URLs.

Plan ref: IMPLEMENTATION_PLAN.md Task 1.3.8.
`boto3` is imported lazily so this module is importable without AWS deps.
"""
from __future__ import annotations

import os


def _require_boto3():  # pragma: no cover - needs boto3 installed
    try:
        import boto3

        return boto3
    except ImportError as exc:
        raise ImportError(
            "boto3 is required for S3Client. Install agent/requirements.txt"
        ) from exc


class S3Client:
    def __init__(
        self,
        endpoint_url: str | None = None,
        region: str | None = None,
        raw_bucket: str | None = None,
        crops_bucket: str | None = None,
    ):
        """Init boto3 s3 client. endpoint_url targets local dev."""
        boto3 = _require_boto3()
        self._s3 = boto3.client(
            "s3",
            region_name=region or os.getenv("AWS_REGION", "us-east-1"),
            endpoint_url=endpoint_url or os.getenv("AWS_ENDPOINT_URL"),
        )
        self.raw_bucket = raw_bucket or os.getenv("S3_RAW_BUCKET", "civic-lens-raw")
        self.crops_bucket = crops_bucket or os.getenv("S3_CROPS_BUCKET", "civic-lens-crops")

    @staticmethod
    def uri(bucket: str, key: str) -> str:
        return f"s3://{bucket}/{key}"

    def upload_video(self, file_path: str, job_id: str) -> str:
        """Upload to civic-lens-raw/{job_id}/video.mp4. Return S3 URI."""
        key = f"{job_id}/video.mp4"
        self._s3.upload_file(file_path, self.raw_bucket, key)
        return self.uri(self.raw_bucket, key)

    def upload_gps(self, file_path: str, job_id: str) -> str:
        """Upload to civic-lens-raw/{job_id}/gps.csv. Return S3 URI."""
        key = f"{job_id}/gps.csv"
        self._s3.upload_file(file_path, self.raw_bucket, key)
        return self.uri(self.raw_bucket, key)

    def upload_crop(self, crop_bytes: bytes, det_id: str) -> str:
        """Upload to civic-lens-crops/{det_id}.jpg. Return S3 URI."""
        key = f"{det_id}.jpg"
        self._s3.put_object(Bucket=self.crops_bucket, Key=key, Body=crop_bytes,
                             ContentType="image/jpeg")
        return self.uri(self.crops_bucket, key)

    def get_presigned_url(self, bucket: str, key: str, expires_in: int = 900) -> str:
        """Generate presigned URL, default 15-min expiry."""
        return self._s3.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_in
        )

    def download_file(self, bucket: str, key: str, local_path: str):
        """Download S3 object to local path."""
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        self._s3.download_file(bucket, key, local_path)
