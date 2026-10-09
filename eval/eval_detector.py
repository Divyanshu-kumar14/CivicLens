#!/usr/bin/env python3
"""Detector eval: classical Canny path vs demo-route YOLO key-frame ground truth.

For each hole: extract its middle key frame, run canny_contours, match the
GT box at IoU>=0.5 -> TP else FN; unmatched extra boxes -> FP.
Prints P/R overall (+ honest note: YOLOv8n numbers need weights + RDD2020).

Usage: python eval/eval_detector.py  (run from repo root)
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import tempfile

import cv2

sys.path.insert(0, os.path.abspath("."))
from vision.classical import canny_contours  # noqa: E402

IOU_THRESH = 0.5
W, H = 960, 540


def _iou(a, b) -> float:
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union else 0.0


def _gt_box(txt_path: str) -> tuple:
    with open(txt_path) as fh:
        cls, cx, cy, w, h = fh.read().split()
    w_px, h_px = float(w) * W, float(h) * H
    return (float(cx) * W - w_px / 2, float(cy) * H - h_px / 2, w_px, h_px)


def main() -> None:
    demo = "eval/datasets/demo-route"
    labels = json.load(open(f"{demo}/labels.json"))
    mid_frame = {h["hole_id"]: (h["frames"][0] + h["frames"][-1]) // 2 for h in labels["holes"]}
    tp = fp = fn = 0
    with tempfile.TemporaryDirectory() as tmp:
        for txt in sorted(glob.glob(f"{demo}/yolo/*.txt")):
            hid = os.path.splitext(os.path.basename(txt))[0]
            frame_no = mid_frame[hid]
            out = f"{tmp}/{hid}.png"
            r = subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", f"{demo}/video.mp4",
                 "-vf", f"select='eq(n,{frame_no})'", "-fps_mode", "passthrough", out],
                capture_output=True)
            if r.returncode != 0 or not os.path.exists(out):
                print(f"  {hid}: frame extract failed -> FN")
                fn += 1
                continue
            img = cv2.imread(out)
            gt = _gt_box(txt)
            boxes = [(b["x"], b["y"], b["w"], b["h"]) for b in canny_contours(img)]
            if any(_iou(gt, b) >= IOU_THRESH for b in boxes):
                tp += 1
                fp += sum(1 for b in boxes if _iou(gt, b) < IOU_THRESH)
            else:
                fn += 1
                fp += len(boxes)
            print(f"  {hid}: frame {frame_no}, {len(boxes)} classical boxes")
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    print(f"\nclassical path on {len(mid_frame)} synthetic key frames: "
          f"TP={tp} FP={fp} FN={fn} -> P={p:.2f} R={r:.2f}")
    print("PRD targets (P>=0.75 R>=0.65, day/night/rain splits) need YOLOv8n + "
          "RDD2020 — this run proves the harness, not the model.")


if __name__ == "__main__":
    main()
