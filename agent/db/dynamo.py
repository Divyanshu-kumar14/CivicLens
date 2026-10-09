"""DynamoDB wrapper: jobs, detections, tickets.

Plan ref: IMPLEMENTATION_PLAN.md Task 1.3.7.
`boto3` is imported lazily so this module is importable without AWS deps.
Table names default to the .env.example values, overridable via env.
"""
from __future__ import annotations

import os
import time

DETECTION_TTL_DAYS = 90


def _require_boto3():  # pragma: no cover - needs boto3 installed
    try:
        import boto3

        return boto3
    except ImportError as exc:
        raise ImportError(
            "boto3 is required for DynamoClient. Install agent/requirements.txt"
        ) from exc


class DynamoClient:
    def __init__(
        self,
        endpoint_url: str | None = None,
        region: str | None = None,
        table_detections: str | None = None,
        table_tickets: str | None = None,
        table_jobs: str | None = None,
    ):
        """Init boto3 dynamodb resource. endpoint_url targets local dev."""
        boto3 = _require_boto3()
        self._dynamo = boto3.resource(
            "dynamodb",
            region_name=region or os.getenv("AWS_REGION", "us-east-1"),
            endpoint_url=endpoint_url or os.getenv("DYNAMO_ENDPOINT_URL"),
        )
        self.t_detections = table_detections or os.getenv("DYNAMO_TABLE_DETECTIONS", "cl-detections")
        self.t_tickets = table_tickets or os.getenv("DYNAMO_TABLE_TICKETS", "cl-tickets")
        self.t_jobs = table_jobs or os.getenv("DYNAMO_TABLE_JOBS", "cl-jobs")

    def _table(self, name: str):
        return self._dynamo.Table(name)

    # --- Jobs ---
    def create_job(self, job: dict) -> str:
        """Put item in cl-jobs. Return job_id."""
        self._table(self.t_jobs).put_item(Item=job)
        return job["job_id"]

    def update_job_status(self, job_id: str, status: str, counts: dict | None = None):
        """Update status + optional counts {raw, clusters, filed, review}."""
        expr = "SET #s = :s, updated_at = :now"
        values: dict = {":s": status, ":now": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if counts:
            expr += ", counts = :c"
            values[":c"] = counts
        self._table(self.t_jobs).update_item(
            Key={"job_id": job_id},
            UpdateExpression=expr,
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues=values,
        )

    def get_job(self, job_id: str) -> dict:
        """Get single job by ID."""
        return self._table(self.t_jobs).get_item(Key={"job_id": job_id}).get("Item", {})

    # --- Detections ---
    def put_detections(self, detections: list[dict]):
        """Batch write detections. Set TTL = now + 90 days."""
        ttl = int(time.time()) + DETECTION_TTL_DAYS * 86400
        with self._table(self.t_detections).batch_writer() as batch:
            for det in detections:
                batch.put_item(Item={**det, "ttl": ttl})

    def get_detections_by_job(self, job_id: str) -> list[dict]:
        """Query GSI job-index."""
        from boto3.dynamodb.conditions import Key

        resp = self._table(self.t_detections).query(
            IndexName="job-index", KeyConditionExpression=Key("job_id").eq(job_id)
        )
        return resp.get("Items", [])

    # --- Tickets ---
    def put_ticket(self, ticket: dict):
        """Put item in cl-tickets."""
        self._table(self.t_tickets).put_item(Item=ticket)

    def update_ticket(self, ticket_id: str, updates: dict):
        """Update specific fields (status, severity, trace append)."""
        expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
        self._table(self.t_tickets).update_item(
            Key={"ticket_id": ticket_id},
            UpdateExpression=expr,
            ExpressionAttributeNames={f"#{k}": k for k in updates},
            ExpressionAttributeValues={f":{k}": v for k, v in updates.items()},
        )

    def get_ticket(self, ticket_id: str) -> dict:
        """Get single ticket."""
        return self._table(self.t_tickets).get_item(Key={"ticket_id": ticket_id}).get("Item", {})

    def query_tickets(self, status: str | None = None, sort_by: str = "severity",
                      projection: str | None = None) -> list[dict]:
        """Query by status using GSI, sort by severity desc.

        projection: optional DynamoDB ProjectionExpression to limit fields
        (Task 3.1.4: drawer opens fetch fewer bytes).
        """
        table = self._table(self.t_tickets)
        kwargs: dict = {}
        if projection:
            kwargs["ProjectionExpression"] = projection
        if status:
            from boto3.dynamodb.conditions import Key

            items = table.query(
                IndexName="status-severity-index",
                KeyConditionExpression=Key("status").eq(status),
                **kwargs,
            ).get("Items", [])
        else:
            items = table.scan(**kwargs).get("Items", [])
        if sort_by == "severity":
            items.sort(key=lambda t: t.get("severity", 0), reverse=True)
        elif sort_by == "timestamp":
            items.sort(key=lambda t: t.get("created_at", ""), reverse=True)
        return items
