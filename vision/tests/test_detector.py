"""Tests for vision/detector.py.

Pure-logic tests (NMS, min-box filter, fusion, IoU) run everywhere.
Model tests skip cleanly when ultralytics/weights/network are unavailable.
"""
import pytest

from vision.detector import Detection, PotholeDetector, filter_min_box, iou, nms

try:
    import ultralytics as _ul  # noqa: F401
    HAS_ULTRALYTICS = True
except ImportError:
    HAS_ULTRALYTICS = False

needs_model = pytest.mark.skipif(not HAS_ULTRALYTICS, reason="ultralytics not installed")


def _det(x=0, y=0, w=50, h=50, conf=0.9, cls="pothole"):
    return Detection(x=x, y=y, w=w, h=h, conf=conf, cls=cls)


def test_iou_full_overlap():
    assert iou(_det(), _det()) == pytest.approx(1.0)


def test_iou_no_overlap():
    assert iou(_det(x=0), _det(x=100)) == pytest.approx(0.0)


def test_min_box_filter():
    dets = [_det(w=50, h=50), _det(w=10, h=60), _det(w=30, h=10)]
    kept = filter_min_box(dets, min_px=24)
    assert len(kept) == 1
    assert (kept[0].w, kept[0].h) == (50, 50)


def test_nms_removes_overlaps():
    a = _det(x=0, y=0, conf=0.9)
    b = _det(x=5, y=5, conf=0.5)  # IoU > 0.5 with a
    c = _det(x=200, y=200, conf=0.8)
    kept = nms([b, a, c], iou_thresh=0.5)
    assert {id(d) for d in kept} == {id(a), id(c)}


def test_fuse_boosts_confirmed():
    yolo = [_det(conf=0.5)]
    classical = [_det(conf=0.4)]
    fused = PotholeDetector.fuse(yolo, classical)
    assert len(fused) == 1
    assert fused[0].conf == pytest.approx(0.6)


def test_fuse_adds_large_classical_only():
    yolo = [_det(x=0, conf=0.9)]
    classical = [_det(x=500, y=500, w=60, h=60, conf=0.4)]  # 3600px, no overlap
    fused = PotholeDetector.fuse(yolo, classical)
    assert len(fused) == 2
    assert fused[1].conf == pytest.approx(0.45)


def test_fuse_drops_sub_threshold_yolo_only():
    yolo = [_det(conf=0.1)]
    assert PotholeDetector.fuse(yolo, [], conf_threshold=0.25) == []


@needs_model
def test_detector_loads_model():
    import yaml

    config = yaml.safe_load(open("config.yaml"))
    det = PotholeDetector(config)
    assert det.conf_threshold == pytest.approx(0.25)
    assert det.min_box_px == 24


@needs_model
def test_detect_returns_detections_on_sample():
    """Run on a known RDD2020 image — needs eval/datasets/rdd2020 + weights."""
    import glob

    import yaml

    from vision.ingest import Frame

    samples = sorted(glob.glob("eval/datasets/rdd2020/*.jpg"))
    if not samples:
        pytest.skip("no RDD2020 sample images yet (Task 1.6)")
    try:
        import cv2
    except ImportError:
        pytest.skip("opencv not installed")
    config = yaml.safe_load(open("config.yaml"))
    det = PotholeDetector(config)
    img = cv2.imread(samples[0])
    dets = det.detect(Frame(image=img, frame_idx=0, timestamp_sec=0.0))
    assert len(dets) >= 1
