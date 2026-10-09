"""Privacy blur: Haar face + plate detection, Gaussian blur masking.

Plan ref: IMPLEMENTATION_PLAN.md Task 2.1.1.
Recall target: >=0.95 faces/plates on the demo set (measured in eval).
Requires opencv + numpy.
"""
from __future__ import annotations

import logging
import os

import cv2
import numpy as np

log = logging.getLogger("civiclens.blur")


def _cascade_search_paths(filename: str) -> list[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    return [
        os.path.join(cv2.data.haarcascades, filename),  # pip wheel (often empty)
        os.path.join(here, "models", filename),  # fetched via scripts/fetch_cascades.py
        os.path.abspath(filename),  # CWD (plan's bare-filename usage)
    ]


def _load_cascade(filename: str) -> cv2.CascadeClassifier:
    for path in _cascade_search_paths(filename):
        if os.path.exists(path):
            clf = cv2.CascadeClassifier(path)
            if not clf.empty():
                return clf
    log.warning("Haar cascade missing: %s — recall will rely on fallback", filename)
    return cv2.CascadeClassifier()


class PrivacyBlur:
    def __init__(self, config: dict):
        """Load Haar cascades; honor privacy.blur_faces / blur_plates flags."""
        priv = config.get("privacy", {})
        self.blur_faces = priv.get("blur_faces", True)
        self.blur_plates = priv.get("blur_plates", True)
        self._face_clf = _load_cascade("haarcascade_frontalface_default.xml")
        # Plan names licence_plate_rus_16stages; upstream equivalent is below.
        self._plate_clf = _load_cascade("haarcascade_russian_plate_number.xml")

    def detect_faces(self, frame: np.ndarray) -> list[tuple]:
        """detectMultiScale faces -> [(x, y, w, h)]. Empty when disabled/missing."""
        if not self.blur_faces or self._face_clf.empty():
            return []
        gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found = self._face_clf.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                                 minSize=(30, 30))
        return [tuple(map(int, r)) for r in found]

    def detect_plates(self, frame: np.ndarray) -> list[tuple]:
        """Haar plates (+ edge-density fallback) -> [(x, y, w, h)]."""
        if not self.blur_plates:
            return []
        regions: list[tuple] = []
        gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if not self._plate_clf.empty():
            found = self._plate_clf.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                                      minSize=(30, 30))
            regions += [tuple(map(int, r)) for r in found]
        regions += self._plate_fallback(gray)
        return regions

    @staticmethod
    def _plate_fallback(gray: np.ndarray) -> list[tuple]:
        """Edge-dense horizontal rectangles (plate-like) the cascade missed."""
        from .classical import canny_contours

        out = []
        for b in canny_contours(gray, min_area=800):
            aspect = b["w"] / max(1, b["h"])
            if 2.0 <= aspect <= 6.0:  # plates are wide, potholes are not
                out.append((b["x"], b["y"], b["w"], b["h"]))
        return out

    @staticmethod
    def blur_regions(frame: np.ndarray, regions: list[tuple], blur_strength: int = 51) -> np.ndarray:
        """GaussianBlur each region in place on a copy. Strength must be odd."""
        if blur_strength % 2 == 0:
            raise ValueError("blur_strength must be odd")
        out = frame.copy()
        h, w = out.shape[:2]
        for (x, y, bw, bh) in regions:
            x1, y1, x2, y2 = max(0, x), max(0, y), min(w, x + bw), min(h, y + bh)
            if x2 > x1 and y2 > y1:
                roi = out[y1:y2, x1:x2]
                out[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (blur_strength, blur_strength), 0)
        return out

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Detect faces + plates, blur all regions, return processed frame."""
        regions = self.detect_faces(frame) + self.detect_plates(frame)
        return self.blur_regions(frame, regions) if regions else frame.copy()

    def process_crop(self, crop: np.ndarray) -> np.ndarray:
        """Blur any faces/plates inside a detection crop before storage."""
        return self.process_frame(crop)
