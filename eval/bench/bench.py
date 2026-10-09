#!/usr/bin/env python3
"""COOL vs stock-OpenCV benchmark: decode -> classical detect -> ORB embed.

Usage: python bench.py --route ../../datasets/demo-route/video.mp4 --runs 3
Measures per run: wall time, throughput fps, per-frame latency (mean/p50/p95),
CPU time. Writes results/{timestamp}_{platform}.json and prints the report table.

This box runs the stock-OpenCV path. Graviton+COOL columns stay TBD until
`make bench` runs on c7g.medium (same command, same route).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import cv2
import numpy as np


def run_once(route: str, sample_fps: float = 2.0) -> dict:
    from vision.classical import canny_contours
    from vision.embedder import DetectionEmbedder
    from vision.ingest import decode_video, validate_video

    meta = validate_video(route)
    embedder = DetectionEmbedder({"embedding": {"dim": 128, "method": "orb"}})
    lat, n_det, cpu0 = [], 0, os.times()
    started = time.monotonic()
    for frame in decode_video(route, sample_fps=sample_fps):
        t0 = time.monotonic()
        for b in canny_contours(frame.image):
            x, y, w, h = b["x"], b["y"], b["w"], b["h"]
            embedder.embed(frame.image[y:y + h, x:x + w])
            n_det += 1
        lat.append((time.monotonic() - t0) * 1000)
    wall = time.monotonic() - started
    cpu = os.times()
    cpu_s = (cpu.user - cpu0.user) + (cpu.system - cpu0.system)
    cores = os.cpu_count() or 1
    lat_sorted = sorted(lat)
    p = lambda q: lat_sorted[min(len(lat_sorted) - 1, int(q * len(lat_sorted)))]
    return {
        "frames": len(lat), "detections": n_det, "wall_s": round(wall, 2),
        "fps": round(len(lat) / wall, 2) if wall else 0.0,
        "lat_mean_ms": round(statistics.mean(lat), 2),
        "lat_p50_ms": round(p(0.50), 2), "lat_p95_ms": round(p(0.95), 2),
        "cpu_s": round(cpu_s, 2),
        "cpu_pct": round(100 * cpu_s / wall / cores, 1) if wall else 0.0,
        "cores": cores,
        "video": {"width": meta["width"], "height": meta["height"], "fps": meta["fps"]},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--sample-fps", type=float, default=2.0)
    args = ap.parse_args()
    runs = [run_once(args.route, args.sample_fps) for _ in range(args.runs)]
    out = {"platform": platform.platform(), "opencv": cv2.__version__,
           "route": args.route, "runs": args.runs, "results": runs}
    os.makedirs("results", exist_ok=True)
    tag = time.strftime("%Y%m%d_%H%M%S")
    path = f"results/{tag}_{platform.machine()}.json"
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)

    fps = [r["fps"] for r in runs]
    print(f"\nroute: {args.route}  ({args.runs} runs, {platform.machine()}, cv2 {cv2.__version__})")
    print(f"| Metric        | stock-OpenCV (this box) | Graviton+COOL (c7g.medium) |")
    print(f"|---------------|-------------------------|----------------------------|")
    print(f"| Throughput    | {statistics.mean(fps):.1f} fps            | TBD                        |")
    print(f"| Latency p95   | {max(r['lat_p95_ms'] for r in runs):.1f} ms           | TBD                        |")
    print(f"| CPU%          | {max(r['cpu_pct'] for r in runs):.0f}%                     | TBD                        |")
    print(f"\nresults -> {path} (gitignored: regenerate via make bench)")


if __name__ == "__main__":
    main()
