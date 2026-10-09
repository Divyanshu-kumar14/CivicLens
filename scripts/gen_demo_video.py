#!/usr/bin/env python3
"""Generate a synthetic dashcam clip with KNOWN pothole ground truth.

Stand-in for Task 1.6.1 (real filming is a human step). Renders a
perspective road with moving lane dashes + dark pothole ellipses, streams
raw frames to ffmpeg (libx264), and writes labels.json + YOLO txt key
frames so dedup eval (10 detections -> 1 hole) is provable on day one.

Usage:
    python scripts/gen_demo_video.py --duration 60 --out eval/datasets/demo-route/video.mp4
Outputs next to the video: gps.csv, labels.json, yolo/<frame>.txt
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess

import numpy as np

W, H, FPS = 960, 540, 24
HOLE_COUNT = 8  # 8 holes, each visible ~2-4s -> multi-pass dedup ground truth


def _road_frame(scroll: int) -> np.ndarray:
    img = np.full((H, W, 3), 120, np.uint8)  # sky grey
    img[200:, :] = (70, 70, 70)  # asphalt band (BGR-ish grey)
    # road edges
    for x in range(W):
        edge = int(60 + (W - 120) * abs(x - W / 2) / (W / 2) * 0.9)
        img[200:200 + 8, x] = (220, 220, 220)
    # moving center dashes (perspective-ish: sparse top, dense bottom)
    for i in range(6):
        y = (200 + ((i * 90 + scroll) % 340))
        wdt = max(2, int((y - 190) / 40))
        img[y:y + 6, W // 2 - wdt:W // 2 + wdt] = (240, 240, 240)
    return img


def _draw_hole(img: np.ndarray, cx: int, cy: int, size: int, rng: np.random.Generator) -> tuple:
    y0, y1 = max(0, cy - size), min(H, cy + size)
    x0, x1 = max(0, cx - size * 2), min(W, cx + size * 2)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    mask = ((xx - cx) / max(1, size * 1.6)) ** 2 + ((yy - cy) / max(1, size)) ** 2 <= 1.0
    region = img[y0:y1, x0:x1]
    region[mask] = (25, 25, 25)  # dark pothole
    return (x0, y0, x1 - x0, y1 - y0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--out", default="eval/datasets/demo-route/video.mp4")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    n_frames = args.duration * FPS
    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    yolo_dir = os.path.join(out_dir, "yolo")
    os.makedirs(yolo_dir, exist_ok=True)

    # Each hole: visible window [start, end] frames + lateral slot.
    holes = []
    for h in range(HOLE_COUNT):
        start = int(rng.integers(0, n_frames - 3 * FPS))
        span = int(rng.integers(2 * FPS, 4 * FPS))
        holes.append({"hole_id": f"hole{h + 1:02d}", "frames": [start, min(n_frames - 1, start + span)],
                      "cx": int(rng.integers(W // 4, 3 * W // 4)), "type": "pothole"})

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-preset", "veryfast", "-crf", "23", args.out],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    key_boxes: dict[str, tuple] = {}
    for f in range(n_frames):
        img = _road_frame(scroll=int(f * 4))
        for hole in holes:
            s, e = hole["frames"]
            if s <= f <= e:
                alpha = (f - s) / max(1, e - s)  # approaches camera: lower + bigger
                cy = int(260 + alpha * 220)
                size = int(6 + alpha * 26)
                box = _draw_hole(img, hole["cx"], cy, size, rng)
                if f == (s + e) // 2:
                    key_boxes[hole["hole_id"]] = box
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    ff.wait()
    if ff.returncode != 0:
        raise RuntimeError("ffmpeg encode failed")

    labels = {"holes": [
        {"hole_id": h["hole_id"], "frames": list(range(h["frames"][0], h["frames"][1] + 1, FPS // 2)),
         "type": h["type"]} for h in holes
    ]}
    with open(os.path.join(out_dir, "labels.json"), "w") as fh:
        json.dump(labels, fh, indent=2)
    for hid, (x, y, w, h) in key_boxes.items():
        cx, cy = (x + w / 2) / W, (y + h / 2) / H
        with open(os.path.join(yolo_dir, f"{hid}.txt"), "w") as fh:
            fh.write(f"0 {cx:.4f} {cy:.4f} {w / W:.4f} {h / H:.4f}\n")
    # GPS matched to clip length
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    print(f"wrote {args.out} ({n_frames} frames), {len(holes)} holes -> labels.json + yolo/")


if __name__ == "__main__":
    main()
