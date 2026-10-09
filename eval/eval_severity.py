#!/usr/bin/env python3
"""Severity eval: system rank vs engineer rank on crafted spanning clusters.

Six synthetic clusters span the severity range in an obvious order; the
engineer ground-truth rank is that order. Reports Spearman rho (target >= 0.7)
plus the per-cluster breakdown for calibration.

Usage: python eval/eval_severity.py  (run from repo root)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath("."))
from agent.services.cluster import Cluster  # noqa: E402
from agent.services.scorer import SeverityScorer  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

CONFIG = {"severity": {"w_area": 0.50, "w_repeat": 0.25, "w_route": 0.15,
                       "w_lane": 0.10, "auto_file_threshold": 70,
                       "review_threshold": 40}}

# (name, repeats, box[x,y,w,h], on_bus_route, engineer_rank 1=worst)
CASES = [
    ("huge-center-bus-x6", 6, [200, 250, 560, 200], True, 1),
    ("big-center-x4", 4, [300, 280, 360, 150], False, 2),
    ("med-center-x3", 3, [400, 300, 160, 100], False, 3),
    ("med-edge-x3", 3, [40, 320, 150, 95], False, 4),
    ("small-edge-x2", 2, [60, 60, 60, 45], False, 5),
    ("tiny-edge-x1", 1, [10, 10, 26, 26], False, 6),
]


def main() -> None:
    scorer = SeverityScorer(CONFIG)
    rows = []
    for name, n, box, bus, human in CASES:
        dets = [{"det_id": f"{name}-{i}", "lat": 12.9, "lon": 77.5,
                 "conf": 0.9, "box": box} for i in range(n)]
        c = Cluster(cluster_id=name, det_ids=[d["det_id"] for d in dets],
                    centroid=(12.9, 77.5), repeat_count=n,
                    representative_det_id=dets[0]["det_id"], detections=dets)
        routes = {"r1": [(12.9, 77.5)]} if bus else None
        s = scorer.score_cluster(c, bus_routes=routes)
        rows.append((name, s.severity, s.classification, human))
    sys_rank = {name: r + 1 for r, (name, _, _, _) in
                enumerate(sorted(rows, key=lambda x: -x[1]))}
    human = [h for _, _, _, h in rows]
    system = [sys_rank[name] for name, _, _, _ in rows]
    rho, _ = spearmanr(human, system)
    for name, sev, cls, h in rows:
        print(f"  {name:20s} severity={sev:3d} ({cls:12s}) human_rank={h} system_rank={sys_rank[name]}")
    print(f"\nSpearman rho={rho:.2f} (target >= 0.70) "
          f"{'PASS' if rho >= 0.70 else 'FAIL'}")


if __name__ == "__main__":
    main()
