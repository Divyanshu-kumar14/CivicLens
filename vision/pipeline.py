"""Main vision orchestrator: video + GPS -> geo-tagged detections with crops.

Plan ref: IMPLEMENTATION_PLAN.md Task 1.2.5.
Phase 2 adds: privacy blur + embeddings (Task 2.1.3) and classical fusion
in the hot loop (Task 2.1.4) — hooks are marked below.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from .config import load_config
from .gps import GPSPoint, interpolate_gps, parse_gps_csv, parse_gps_srt

if TYPE_CHECKING:  # pragma: no cover
    from .detector import Detection
    from .ingest import Frame


@dataclass
class ProcessingResult:
    job_id: str
    detections: list[Detection] = field(default_factory=list)
    total_frames: int = 0
    processed_frames: int = 0
    duration_sec: float = 0.0
    fps: float = 0.0


class VisionPipeline:
    def __init__(self, config_path: str = "config.yaml", detector=None, blur=None,
                 embedder=None, output_dir: str = "data/crops"):
        """Load config; use injected deps or build them (Task 2.1.3).

        `detector`/`blur`/`embedder` injection keeps this class testable
        without YOLO weights or cv2. Missing cv2 degrades blur/embed to None
        (detect-only mode) instead of failing import.
        """
        import logging

        self.config = load_config(config_path)
        if detector is None:
            from .detector import PotholeDetector

            detector = PotholeDetector(self.config)
        self.detector = detector
        self.output_dir = output_dir
        if blur is None or embedder is None:
            try:
                from .blur import PrivacyBlur
                from .embedder import DetectionEmbedder

                blur = PrivacyBlur(self.config) if blur is None else blur
                embedder = DetectionEmbedder(self.config) if embedder is None else embedder
            except ImportError as exc:
                logging.getLogger("civiclens.pipeline").warning(
                    "CV stack missing, blur/embed disabled: %s", exc
                )
        self.blur = blur
        self.embedder = embedder

    def _detect(self, frame: Frame) -> list[Detection]:
        """Fused detection when the detector supports it, else plain detect."""
        fused = getattr(self.detector, "detect_with_fusion", None)
        if callable(fused):
            return fused(frame)
        return self.detector.detect(frame)

    def process_frame(self, frame: Frame, gps: GPSPoint) -> list[Detection]:
        """Single-frame path (also used for live demo): detect + geo-tag."""
        dets = self._detect(frame)
        # NOTE: classical fusion now lives in detect_with_fusion (Task 2.1.4).
        for det in dets:
            det.lat, det.lon, det.heading = gps.lat, gps.lon, gps.heading
        return dets

    def process_video(
        self,
        video_path: str,
        gps_path: str,
        job_id: str,
        sample_fps: float = 2.0,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> ProcessingResult:
        """Full batch path: validate -> GPS parse -> per-frame detect -> crops."""
        import cv2  # needs the CV stack
        import numpy as np

        from .ingest import decode_video, validate_video

        started = time.monotonic()
        meta = validate_video(video_path)
        total = meta.get("num_frames", 0)
        if gps_path.lower().endswith(".srt"):
            gps_points = parse_gps_srt(gps_path)
        else:
            gps_points = parse_gps_csv(gps_path)
        os.makedirs(self.output_dir, exist_ok=True)

        detections: list[Detection] = []
        processed = 0
        for frame in decode_video(video_path, sample_fps=sample_fps):
            gps = interpolate_gps(gps_points, frame.timestamp_sec)
            for det in self.process_frame(frame, gps):
                h, w = frame.image.shape[:2]
                x1, y1 = max(0, det.x), max(0, det.y)
                x2, y2 = min(w, det.x + det.w), min(h, det.y + det.h)
                if x2 > x1 and y2 > y1:
                    raw_crop = frame.image[y1:y2, x1:x2]
                    # Embed BEFORE blur (raw features), blur before storage.
                    if self.embedder is not None:
                        det.embedding = self.embedder.embed(raw_crop)
                        np.save(os.path.join(self.output_dir, f"{det.det_id}.npy"),
                                det.embedding)
                    crop = self.blur.process_crop(raw_crop) if self.blur else raw_crop
                    crop_path = os.path.join(self.output_dir, f"{det.det_id}.jpg")
                    cv2.imwrite(crop_path, crop)
                    det.crop_path = crop_path
                detections.append(det)
            processed += 1
            if progress_cb is not None:
                progress_cb(processed, total)

        duration = time.monotonic() - started
        return ProcessingResult(
            job_id=job_id,
            detections=detections,
            total_frames=total,
            processed_frames=processed,
            duration_sec=duration,
            fps=(processed / duration) if duration > 0 else 0.0,
        )
