#!/usr/bin/env python3
"""Pre-seed DynamoDB + S3 with demo data (`make seed-demo`).

Writes a demo completed job + a handful of tickets so the map works
before any video is processed. Targets localstack when DYNAMO_ENDPOINT_URL
/ AWS_ENDPOINT_URL are set, else real AWS.
"""
from __future__ import annotations

import time

WARD = "ward-12-demo"
DEMO_TICKETS = [
    ("t_hole01", 12.9716, 77.5946, 82, "filed", 6),
    ("t_hole02", 12.9730, 77.5960, 64, "pending", 3),
    ("t_hole03", 12.9690, 77.5920, 45, "pending", 2),
    ("t_hole04", 12.9750, 77.5980, 28, "dismissed", 1),
    ("t_hole05", 12.9700, 77.5990, 74, "filed", 5),
]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def main() -> None:
    from agent.db.dynamo import DynamoClient

    db = DynamoClient()
    job_id = "job-demo-seed"
    db.create_job({
        "job_id": job_id, "ward": WARD, "status": "completed",
        "progress_pct": 100.0,
        "counts": {"raw": 100, "clusters": 12, "filed": 5, "review": 4, "dismissed": 3},
        "created_at": _now(), "updated_at": _now(),
    })
    for tid, lat, lon, sev, status, repeat in DEMO_TICKETS:
        db.put_ticket({
            "ticket_id": tid, "hole_label": tid.replace("t_", ""), "det_ids": [],
            "centroid": [lat, lon], "repeat_count": repeat, "severity": sev,
            "status": status,
            "signals": {"area_norm": sev, "repeat": min(100, repeat * 20),
                        "bus_route_w": 0, "center_lane": 30},
            "trace": [{"ts": _now(), "actor": "agent", "from_status": "new",
                       "to_status": status, "reasons": ["seeded"], "signals": {}}],
            "created_at": _now(), "updated_at": _now(),
        })
    print(f"seeded job {job_id} + {len(DEMO_TICKETS)} tickets")


if __name__ == "__main__":
    main()
