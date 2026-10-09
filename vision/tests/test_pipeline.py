"""Tests for vision/pipeline.py — injected fakes, no CV stack needed."""
from types import SimpleNamespace

from vision.gps import GPSPoint
from vision.pipeline import ProcessingResult, VisionPipeline


class _FakeDetector:
    def __init__(self, dets):
        self._dets = dets
        self.calls = 0

    def detect(self, frame):
        self.calls += 1
        return list(self._dets)


def _pipe(tmp_path, dets=()):
    # Pipeline reads config from disk; point it at the repo config.
    return VisionPipeline(config_path="config.yaml", detector=_FakeDetector(list(dets)))


def test_processing_result_defaults():
    r = ProcessingResult(job_id="j1")
    assert r.detections == [] and r.processed_frames == 0 and r.fps == 0.0


def test_process_frame_assigns_gps():
    from vision.detector import Detection

    dets = [Detection(x=1, y=2, w=30, h=30, conf=0.8)]
    pipe = _pipe(None, dets)
    frame = SimpleNamespace(image=None, frame_idx=7, timestamp_sec=3.5)
    gps = GPSPoint(t=3.5, lat=12.9, lon=77.5, heading=90.0)
    out = pipe.process_frame(frame, gps)
    assert len(out) == 1
    assert (out[0].lat, out[0].lon, out[0].heading) == (12.9, 77.5, 90.0)
    assert pipe.detector.calls == 1
