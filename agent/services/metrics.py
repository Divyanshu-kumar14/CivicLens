"""CloudWatch metrics publisher (namespace CivicLens).

Plan ref: IMPLEMENTATION_PLAN.md Task 3.1.1.
boto3 is lazy; inject a fake client in tests. Every publish is best-effort —
metrics must never break the request path.
"""
from __future__ import annotations

import logging
import os
import time

log = logging.getLogger("civiclens.metrics")
NAMESPACE = "CivicLens"


class MetricsPublisher:
    def __init__(self, client=None, namespace: str = NAMESPACE, enabled: bool = True):
        """client: boto3 cloudwatch client (built lazily when None)."""
        self.namespace = namespace
        self.enabled = enabled and os.getenv("METRICS_ENABLED", "1") == "1"
        self._client = client

    def _cw(self):
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "cloudwatch",
                region_name=os.getenv("AWS_REGION", "us-east-1"),
                endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
            )
        return self._client

    def publish(self, metric_name: str, value: float, unit: str = "None",
                dimensions: dict | None = None):
        """Emit one datapoint. Swallows backend errors (logged)."""
        if not self.enabled:
            return
        try:
            self._cw().put_metric_data(
                Namespace=self.namespace,
                MetricData=[{
                    "MetricName": metric_name,
                    "Value": value,
                    "Unit": unit,
                    "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "Dimensions": [{"Name": k, "Value": str(v)}
                                   for k, v in (dimensions or {}).items()],
                }],
            )
        except Exception as exc:
            log.warning("metric %s dropped: %s", metric_name, exc)

    def job_completed(self, counts: dict, duration_min: float, fps: float):
        """Standard per-job metric set (worker calls this once per job)."""
        raw = counts.get("raw", 0)
        clustered = counts.get("clusters", 0) or 1
        self.publish("fps", fps, "Count/Second")
        self.publish("job_duration_min", duration_min, "None")
        self.publish("dedup_ratio", raw / clustered, "None")
        self.publish("tickets_filed", counts.get("filed", 0), "Count")
        self.publish("tickets_pending", counts.get("review", 0), "Count")
