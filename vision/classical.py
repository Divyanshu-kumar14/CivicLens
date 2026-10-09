"""Classical CV fallback: Canny + contour helpers for pothole fusion.

Plan ref: IMPLEMENTATION_PLAN.md Task 1.2.4.
Used to confirm borderline YOLO detections (conf 0.25-0.40) and to catch
large defects YOLO missed. Requires opencv + numpy (imported at top —
callers without CV deps must import this module lazily).
"""
from __future__ import annotations

import cv2
import numpy as np

CANNY_THRESH1 = 50
CANNY_THRESH2 = 150
MIN_CONTOUR_AREA = 500
MIN_ASPECT = 0.3
MAX_ASPECT = 3.0


def canny_contours(
    gray: np.ndarray,
    thresh1: int = CANNY_THRESH1,
    thresh2: int = CANNY_THRESH2,
    min_area: int = MIN_CONTOUR_AREA,
) -> list[dict]:
    """Blur -> Canny -> dilate -> contours, filtered by area + aspect ratio.

    Accepts a grayscale or BGR image. Returns [{x, y, w, h, area,
    aspect_ratio}] sorted by area descending.
    """
    if gray.ndim == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, thresh1, thresh2)
    closed = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[dict] = []
    for cnt in contours:
        area = float(cv2.contourArea(cnt))
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        if h == 0:
            continue
        aspect = w / h
        if not (MIN_ASPECT <= aspect <= MAX_ASPECT):
            continue
        boxes.append({"x": x, "y": y, "w": w, "h": h, "area": area, "aspect_ratio": aspect})
    boxes.sort(key=lambda b: b["area"], reverse=True)
    return boxes


def perspective_area(box: dict, frame_height: int) -> float:
    """Real-world area proxy in 0-1 using vertical position as depth cue.

    Objects lower in frame are closer to the camera, so the same defect
    covers more pixels there. We divide apparent area by a depth scale
    (>=0.2, 1.0 at the frame bottom) and normalize against frame size:

        norm = (area / frame_height^2) / max(0.2, y_bottom / frame_height)
    """
    depth = min(max((box["y"] + box["h"]) / max(1, frame_height), 0.0), 1.0)
    norm = (box["area"] / (max(1, frame_height) ** 2)) / max(0.2, depth)
    return min(max(norm, 0.0), 1.0)


def is_center_lane(box: dict, frame_width: int, lane_fraction: float = 0.6) -> bool:
    """True if the box center falls inside the center `lane_fraction` of the frame."""
    cx = box["x"] + box["w"] / 2.0
    half = frame_width * lane_fraction / 2.0
    return abs(cx - frame_width / 2.0) <= half
