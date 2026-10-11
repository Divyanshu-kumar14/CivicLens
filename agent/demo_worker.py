"""Classical-only demo worker for small boxes (no torch/ultralytics/YOLO).

The full vision image (torch CPU + YOLO, ~2.7GB) does not fit a 2GB demo
box alongside the API. This worker processes SQS jobs with the classical
Canny+contour detector only: sample frames @2fps -> classical boxes -> GPS
interpolate -> crops -> the SAME cluster/score/file pipeline as production.

Honest limitations (also noted in the advancement file):
- No visual embeddings without torch: every detection shares a constant
  embedding, so dedup merges on GPS proximity alone (15m eps). Co-located
  distinct holes merge; that is the documented trade for fitting in RAM.
- No privacy blur on this path.
- GPS file missing -> ward-center fallback with per-detection spread.

Run on the box with the agent image (carries opencv-headless):
    python -m agent.demo_worker
"""
from __future__ import annotations

import logging
import os
import tempfile
import time
import uuid
from types import SimpleNamespace

from agent.worker import BatchWorker

log = logging.getLogger("civiclens.demo_worker")

try:
    # Local dev / tests: full repo on sys.path. Agent image: minimal torch-free
    # vision package (see infra/Dockerfile.agent) — same import path both places.
    from vision.classical import canny_contours
    from vision.gps import interpolate_gps, parse_gps_csv, parse_gps_srt
except ImportError:  # pragma: no cover - packaging fallback
    from cv_classical import canny_contours
    from gps_util import interpolate_gps, parse_gps_csv, parse_gps_srt

SAMPLE_FPS = 2.0
MAX_WIDTH = 960
MAX_BOXES_PER_FRAME = 3
MIN_AREA_PX = 500
WARD_FALLBACK = (12.9685, 77.5985)  # ward center (matches web map default)


def _conf_for_area(area: float) -> float:
    """Area-proportional confidence: big close holes score high, specks low."""
    return round(min(0.9, 0.45 + area / 30000.0), 2)


class DemoWorker(BatchWorker):
    """BatchWorker with a classical-only process_job (see module docstring)."""

    def process_job(self, job: dict) -> dict:
        """processing -> download -> classical detect -> store -> agent loop."""
        import cv2
        import numpy as np

        job_id = job["job_id"]
        self.db.update_job_status(job_id, "processing")
        clusterer, scorer, filer = self._services()

        with tempfile.TemporaryDirectory(prefix=f"cl-demo-{job_id}-") as tmp:
            video_local = os.path.join(tmp, "video.mp4")
            gps_local = os.path.join(tmp, "gps.csv")
            self._download(job["video_url"], video_local)
            gps_points = None
            if job.get("gps_url"):
                self._download(job["gps_url"], gps_local)
                try:
                    gps_points = (parse_gps_srt(gps_local) if gps_local.endswith(".srt")
                                  else parse_gps_csv(gps_local))
                except Exception as exc:
                    log.warning("job %s: GPS parse failed (%s), using fallback", job_id, exc)
                    gps_points = None

            detections = self._detect_classical(video_local, gps_points, tmp)
            det_dicts = self._store_detections(job_id, detections, tmp)
            clusters = clusterer.cluster_detections(det_dicts)
            counts = {"raw": len(det_dicts), "clusters": len(clusters),
                      "filed": 0, "review": 0, "dismissed": 0}
            for cluster in clusters:
                ticket = filer.process_cluster(scorer.score_cluster(cluster),
                                               webhook_url=self.webhook_url)
                counts[{"filed": "filed", "pending": "review",
                        "dismissed": "dismissed"}[ticket["status"]]] += 1

        self.db.update_job_status(job_id, "completed", counts)
        log.info("job %s completed: %s", job_id, counts)
        return counts

    def _detect_classical(self, video_path: str, gps_points, tmp: str) -> list:
        """Sample @2fps, Canny boxes, GPS-tagged detection objects for
        BatchWorker._store_detections (needs crop_path/det_id/embedding/etc)."""
        import cv2
        import numpy as np

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"cannot open video: {video_path}")
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        step = max(1, round(src_fps / SAMPLE_FPS))
        crops_dir = os.path.join(tmp, "crops")
        os.makedirs(crops_dir, exist_ok=True)

        detections, idx, kept = [], 0, 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if idx % step != 0:
                    idx += 1
                    continue
                ts = idx / src_fps
                idx += 1
                h, w = frame.shape[:2]
                if w > MAX_WIDTH:
                    frame = cv2.resize(frame, (MAX_WIDTH, round(MAX_WIDTH * h / w)))
                    h, w = frame.shape[:2]
                for b in canny_contours(frame, min_area=MIN_AREA_PX)[:MAX_BOXES_PER_FRAME]:
                    x, y, bw, bh = b["x"], b["y"], b["w"], b["h"]
                    pad = 0.1
                    x0, y0 = max(0, int(x - bw * pad)), max(0, int(y - bh * pad))
                    x1, y1 = min(w, int(x + bw * (1 + pad))), min(h, int(y + bh * (1 + pad)))
                    det_id = f"d_{uuid.uuid4().hex[:10]}"
                    crop_path = os.path.join(crops_dir, f"{det_id}.jpg")
                    cv2.imwrite(crop_path, frame[y0:y1, x0:x1])
                    lat, lon = self._locate(gps_points, ts, kept)
                    detections.append(SimpleNamespace(
                        det_id=det_id, crop_path=crop_path, timestamp_sec=ts,
                        lat=lat, lon=lon, cls="pothole",
                        conf=_conf_for_area(b["area"]),
                        x=x, y=y, w=bw, h=bh,
                        # No torch here: constant embedding => dedup merges
                        # on GPS proximity alone (documented trade).
                        embedding=np.ones(8, dtype=float),
                    ))
                    kept += 1
        finally:
            cap.release()
        log.info("classical detect: %d detections", len(detections))
        return detections

    @staticmethod
    def _locate(gps_points, ts: float, n: int) -> tuple[float, float]:
        if gps_points:
            try:
                g = interpolate_gps(gps_points, ts)
                return g.lat, g.lon
            except Exception:
                pass
        # No usable GPS: ward-center fallback, spread so pins don't stack.
        return WARD_FALLBACK[0] + (n % 5) * 0.0004, WARD_FALLBACK[1] + (n // 5) * 0.0004


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    DemoWorker().poll_and_process()
