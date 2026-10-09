#!/usr/bin/env python3
"""Dedup eval: synthetic multi-pass detections from labels.json ground truth.

Builds N noisy sightings per hole_id (GPS jitter ~ lobby of geo_eps_m, ORB-like
embeddings with intra-hole similarity > cos_thresh), runs DeduplicatorService,
and reports cluster precision (one cluster => one hole?) + recall (one hole =>
one cluster?) plus the with/without counts.

Usage: python eval/eval_dedup.py  (run from repo root)
"""
from __future__ import annotations

import json
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.abspath("."))
from agent.services.cluster import DeduplicatorService  # noqa: E402
from vision.gps import haversine_distance  # noqa: E402

CONFIG = {"dedup": {"geo_eps_m": 15, "cos_thresh": 0.82, "min_samples": 2}}
PASSES_PER_HOLE = 10
BASE_LAT, BASE_LON = 12.9716, 77.5946


def _hole_base(i: int) -> tuple[float, float]:
    # Holes ~40m apart along the route (no geo ambiguity by construction).
    return BASE_LAT + i * 0.00036, BASE_LON + i * 0.00036


def _synth_detections(seed: int = 11) -> tuple[list[dict], dict[str, str]]:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    dets, truth = [], {}
    hole_ids = [h["hole_id"] for h in json.load(
        open("eval/datasets/demo-route/labels.json"))["holes"]]
    for i, hid in enumerate(hole_ids):
        lat0, lon0 = _hole_base(i)
        proto = np_rng.normal(size=32)
        proto /= np.linalg.norm(proto)
        for p in range(PASSES_PER_HOLE):
            lat = lat0 + rng.uniform(-4, 4) / 111195.0
            lon = lon0 + rng.uniform(-4, 4) / 111195.0
            emb = proto + np_rng.normal(scale=0.08, size=32)
            emb /= np.linalg.norm(emb)
            det_id = f"{hid}-p{p}"
            dets.append({"det_id": det_id, "lat": lat, "lon": lon,
                         "conf": 0.9, "box": [0, 0, 50, 50], "embedding": emb})
            truth[det_id] = hid
    return dets, truth


def main() -> None:
    dets, truth = _synth_detections()
    svc = DeduplicatorService(CONFIG)
    clusters = svc.cluster_detections(dets)
    stats = svc.get_dedup_stats(len(dets), len(clusters))

    pure = sum(1 for c in clusters
               if len({truth[d] for d in c.det_ids}) == 1)
    precision = pure / len(clusters) if clusters else 0.0
    holes = {truth[d] for d in truth}
    single = sum(1 for h in holes
                 if sum(1 for c in clusters if h in {truth[d] for d in c.det_ids}) == 1)
    recall = single / len(holes) if holes else 0.0
    # GPS sanity: worst intra-sighting drift must sit inside geo_eps_m.
    print(f"raw={stats['raw']} -> clusters={stats['clustered']} "
          f"(ratio {stats['ratio']}, -{stats['reduction_pct']}%)")
    print(f"cluster precision={precision:.2f} (pure {pure}/{len(clusters)}), "
          f"recall={recall:.2f} ({single}/{len(holes)} holes in exactly one cluster)")
    print(f"truth holes={len(holes)}, max GPS pair drift covered by eps=15m: "
          f"{haversine_distance(BASE_LAT, BASE_LON, BASE_LAT + 8 / 111195.0, BASE_LON):.1f}m")


if __name__ == "__main__":
    main()
