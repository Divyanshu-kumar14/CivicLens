"""Tests for agent/services/scorer.py."""
import pytest

from agent.services.cluster import Cluster
from agent.services.scorer import SeverityScorer

CONFIG = {"severity": {"w_area": 0.50, "w_repeat": 0.25, "w_route": 0.15,
                       "w_lane": 0.10, "auto_file_threshold": 70,
                       "review_threshold": 40}}


def _cluster(n=1, box=None, lat=12.9716, lon=77.5946):
    box = box or [200, 250, 560, 200]  # large, center-lane (area_norm ~46)
    dets = [{"det_id": f"d{i}", "lat": lat, "lon": lon, "conf": 0.9, "box": box}
            for i in range(n)]
    return Cluster(cluster_id="c1", det_ids=[d["det_id"] for d in dets],
                   centroid=(lat, lon), repeat_count=n,
                   representative_det_id=dets[0]["det_id"], detections=dets)


def test_big_centered_repeat_auto_files():
    scorer = SeverityScorer(CONFIG)
    bus = {"r1": [(12.9716, 77.5946)]}
    scored = scorer.score_cluster(_cluster(n=6), bus_routes=bus)
    assert scored.severity >= 70
    assert scored.classification == "auto_file"
    assert set(scored.signals) == {"area_norm", "repeat", "bus_route_w", "center_lane"}


def test_tiny_single_offlane_dismisses():
    scorer = SeverityScorer(CONFIG)
    scored = scorer.score_cluster(_cluster(n=1, box=[10, 10, 26, 26]))
    assert scored.severity < 40
    assert scored.classification == "auto_dismiss"


def test_mid_case_reviews():
    scorer = SeverityScorer(CONFIG)
    assert scorer.classify(69) == "review"
    assert scorer.classify(40) == "review"


def test_classify_boundaries():
    scorer = SeverityScorer(CONFIG)
    assert scorer.classify(100) == "auto_file"
    assert scorer.classify(70) == "auto_file"
    assert scorer.classify(39) == "auto_dismiss"
    assert scorer.classify(0) == "auto_dismiss"
