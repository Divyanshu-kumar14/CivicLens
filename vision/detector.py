"""YOLOv8n + classical fusion pothole detector.

Plan ref: IMPLEMENTATION_PLAN.md Task 1.2.3.
`ultralytics`, `cv2` and `numpy` are imported lazily so this module (and its
pure helpers `iou` / `nms` / `filter_min_box` / `fuse`) is usable in tests
and hosts without the CV stack. Only `PotholeDetector.__init__` /
`detect` / `detect_classical` need the heavy deps.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    import numpy as np

    from .ingest import Frame

FUSE_IOU = 0.3
FUSE_BOOST = 0.1
CLASSICAL_ONLY_MIN_AREA = 1000
CLASSICAL_ONLY_CONF = 0.45
CLASSICAL_FALLBACK_CONF = 0.4


@dataclass
class Detection:
    det_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    cls: str = "pothole"  # 'pothole' | 'crack'
    conf: float = 0.0
    frame_idx: int = 0
    timestamp_sec: float = 0.0
    lat: float = 0.0
    lon: float = 0.0
    heading: float = 0.0
    crop_path: str = ""
    embedding: Any = None  # np.ndarray (128,) once Phase 2 embedder runs


def _box(det) -> tuple:
    return (det.x, det.y, det.w, det.h)


def iou(a, b) -> float:
    """Intersection-over-union of two (x, y, w, h) boxes or Detections."""
    ax, ay, aw, ah = _box(a) if isinstance(a, Detection) else a
    bx, by, bw, bh = _box(b) if isinstance(b, Detection) else b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def nms(dets: list[Detection], iou_thresh: float = 0.5) -> list[Detection]:
    """Greedy NMS: highest-conf box survives each IoU > thresh cluster."""
    kept: list[Detection] = []
    for det in sorted(dets, key=lambda d: d.conf, reverse=True):
        if all(iou(det, k) <= iou_thresh for k in kept):
            kept.append(det)
    return kept


def filter_min_box(dets: list[Detection], min_px: int) -> list[Detection]:
    """Drop detections smaller than min_px in either dimension."""
    return [d for d in dets if d.w >= min_px and d.h >= min_px]


class PotholeDetector:
    def __init__(self, config: dict):
        """Load YOLO weights + thresholds from the `detection` config section."""
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "ultralytics is required for PotholeDetector. "
                "Install vision/requirements.txt"
            ) from exc
        det_cfg = config["detection"]
        self.model = YOLO(det_cfg.get("model", "yolov8n") + ".pt")
        self.conf_threshold = det_cfg.get("conf_threshold", 0.25)
        self.nms_iou = det_cfg.get("nms_iou", 0.5)
        self.min_box_px = det_cfg.get("min_box_px", 24)
        self.classes: list[str] = det_cfg.get("classes", ["pothole", "crack"])

    def detect(self, frame: Frame) -> list[Detection]:
        """YOLO inference -> conf/min-box/class filter -> NMS -> Detections."""
        results = self.model.predict(
            frame.image, verbose=False, conf=self.conf_threshold, iou=self.nms_iou
        )[0]
        names = results.names
        dets: list[Detection] = []
        for box in results.boxes:
            cls_name = names[int(box.cls[0])]
            if cls_name not in self.classes:
                continue
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
            w, h = x2 - x1, y2 - y1
            if w < self.min_box_px or h < self.min_box_px:
                continue
            dets.append(
                Detection(
                    x=x1, y=y1, w=w, h=h, cls=cls_name,
                    conf=float(box.conf[0]), frame_idx=frame.frame_idx,
                    timestamp_sec=frame.timestamp_sec,
                )
            )
        return nms(dets, self.nms_iou)

    def detect_classical(self, frame: Frame, roi: tuple | None = None) -> list[Detection]:
        """Classical fallback on full frame or an (x, y, w, h) ROI.

        Returns conf=0.4 'pothole' candidates for fusion confirmation.
        """
        from .classical import canny_contours

        img = frame.image
        ox, oy = 0, 0
        if roi is not None:
            ox, oy, rw, rh = roi
            img = img[oy : oy + rh, ox : ox + rw]
        return [
            Detection(
                x=b["x"] + ox, y=b["y"] + oy, w=b["w"], h=b["h"],
                cls="pothole", conf=CLASSICAL_FALLBACK_CONF,
                frame_idx=frame.frame_idx, timestamp_sec=frame.timestamp_sec,
            )
            for b in canny_contours(img)
        ]

    @staticmethod
    def fuse(
        yolo_dets: list[Detection], classical_dets: list[Detection], conf_threshold: float = 0.25
    ) -> list[Detection]:
        """Fuse YOLO + classical candidates.

        - YOLO det overlapping (IoU > 0.3) a classical det: conf +0.1 (cap 1.0).
        - Classical-only det with area > 1000px: added at conf=0.45.
        - YOLO-only dets below conf_threshold are dropped.
        """
        fused: list[Detection] = []
        for det in yolo_dets:
            if any(iou(det, c) > FUSE_IOU for c in classical_dets):
                det.conf = min(1.0, det.conf + FUSE_BOOST)
            if det.conf >= conf_threshold:
                fused.append(det)
        for cdet in classical_dets:
            if cdet.w * cdet.h > CLASSICAL_ONLY_MIN_AREA and not any(
                iou(cdet, d) > FUSE_IOU for d in yolo_dets
            ):
                cdet.conf = CLASSICAL_ONLY_CONF
                fused.append(cdet)
        return fused
