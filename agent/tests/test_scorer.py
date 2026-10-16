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
    assert set(scored.signals) == {"area_norm", "repeat", "bus_route_w", "center_lane",
                                     "contributions", "thresholds"}


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


def test_signals_carry_contributions_and_thresholds():
    from agent.services.scorer import explain_decision

    scorer = SeverityScorer(CONFIG)
    scored = scorer.score_cluster(_cluster(n=6),
                                  bus_routes={"r1": [(12.9716, 77.5946)]})
    contrib = scored.signals["contributions"]
    assert set(contrib) == {"area", "repeat", "route", "lane"}
    # Contributions reconstruct the severity (modulo rounding).
    assert sum(contrib.values()) == pytest.approx(scored.severity, abs=1.0)
    assert scored.signals["thresholds"] == {"auto_file": 70, "review": 40}
    reasons = explain_decision(scored)
    assert reasons[0] == f"severity {scored.severity} >= 70"
    assert any("largest contributor" in r for r in reasons)
    assert any("6 passes" in r for r in reasons)


def test_explain_dismiss_and_review_bands():
    from agent.services.scorer import ScoredCluster, explain_decision

    def _s(sev):
        return ScoredCluster(cluster_id="c", det_ids=["d"], centroid=(0, 0),
                             repeat_count=1, representative_det_id="d",
                             detections=[], severity=sev, classification="x",
                             signals={"area_norm": 10, "repeat": 20,
                                      "bus_route_w": 0.0, "center_lane": 30.0,
                                      "thresholds": {"auto_file": 70,
                                                     "review": 40}})

    assert explain_decision(_s(20))[0] == "low_severity"
    assert explain_decision(_s(69))[0] == "human review required"
    assert explain_decision(_s(40))[0] == "human review required"
    assert explain_decision(_s(70))[0] == "severity 70 >= 70"
    # Arterial + critical never auto-files, even at 95.
    forced = explain_decision(_s(95), arterial=True)
    assert forced[0] == "human review required"
    assert any("arterial" in r for r in forced)
    # Same severity off-arterial files.
    assert explain_decision(_s(95))[0] == "severity 95 >= 70"
