#!/usr/bin/env python3
"""Simple labeling helper: extract frames every N for manual YOLO labeling.

Usage:
    python scripts/label_tool.py eval/datasets/demo-route/video.mp4 --every 48 --outdir eval/datasets/demo-route/frames
Then label frames with any YOLO tool (class 0 = pothole, 1 = crack) and
group multi-pass sightings by hole_id in labels.json (see Task 1.6.3).
"""
from __future__ import annotations

import argparse
import os
import subprocess


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--every", type=int, default=48, help="extract every Nth frame")
    ap.add_argument("--outdir", default="eval/datasets/demo-route/frames")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", args.video, "-vf", f"select='not(mod(n,{args.every}))'",
         "-fps_mode", "passthrough", os.path.join(args.outdir, "frame_%05d.jpg")],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-500:]}")
    n = len([f for f in os.listdir(args.outdir) if f.endswith(".jpg")])
    print(f"extracted {n} frames -> {args.outdir}")


if __name__ == "__main__":
    main()
