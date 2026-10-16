"""Tests for agent/services/cluster.py."""
import pytest

from agent.services.cluster import DeduplicatorService, cosine_sim, is_valid_geo

CONFIG = {"dedup": {"geo_eps_m": 15, "cos_thresh": 0.82, "min_samples": 2}}


def _det(det_id, lat, lon, conf=0.9, emb=None):
    return {"det_id": det_id, "lat": lat, "lon": lon, "conf": conf,
            "box": [0, 0, 50, 50],
            "embedding": emb if emb is not None else [1.0, 0.0, 0.0]}


def test_cosine_basics():
    assert cosine_sim([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine_sim([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine_sim(None, [1]) == 0.0
    assert cosine_sim([0, 0], [1, 0]) == 0.0


def test_close_similar_deduplicate():
    svc = DeduplicatorService(CONFIG)
    dets = [_det("a", 12.97160, 77.59460), _det("b", 12.97163, 77.59463)]  # ~5m apart
    clusters = svc.cluster_detections(dets)
    assert len(clusters) == 1
    assert clusters[0].repeat_count == 2
    assert set(clusters[0].det_ids) == {"a", "b"}
    assert clusters[0].centroid[0] == pytest.approx(12.971615)


def test_far_apart_stay_split():
    svc = DeduplicatorService(CONFIG)
    dets = [_det("a", 12.9716, 77.5946), _det("b", 12.9800, 77.6000)]  # ~1km
    assert len(svc.cluster_detections(dets)) == 2


def test_close_but_visually_different_stay_split():
    svc = DeduplicatorService(CONFIG)
    dets = [_det("a", 12.97160, 77.59460, emb=[1.0, 0.0, 0.0]),
            _det("b", 12.97163, 77.59463, emb=[0.0, 1.0, 0.0])]
    assert len(svc.cluster_detections(dets)) == 2


def test_weak_solo_noise_dismissed():
    svc = DeduplicatorService(CONFIG)
    assert svc.cluster_detections([_det("a", 12.9, 77.5, conf=0.3)]) == []


def test_strong_solo_survives():
    svc = DeduplicatorService(CONFIG)
    clusters = svc.cluster_detections([_det("a", 12.9, 77.5, conf=0.9)])
    assert len(clusters) == 1 and clusters[0].repeat_count == 1


def test_dedup_stats():
    stats = DeduplicatorService.get_dedup_stats(100, 12)
    assert stats == {"raw": 100, "clustered": 12, "ratio": 8.33, "reduction_pct": 88.0}


def test_invalid_gps_shapes():
    assert is_valid_geo(12.9, 77.5)
    assert not is_valid_geo(None, 77.5)
    assert not is_valid_geo(12.9, None)
    assert not is_valid_geo(float("nan"), 77.5)
    assert not is_valid_geo(12.9, float("nan"))
    assert not is_valid_geo(91.0, 77.5)
    assert not is_valid_geo(12.9, 181.0)
    assert not is_valid_geo("bad", 77.5)


def test_missing_and_invalid_gps_dropped_not_merged(caplog):
    svc = DeduplicatorService(CONFIG)
    dets = [
        _det("good", 12.9716, 77.5946),
        {"det_id": "nogps", "conf": 0.9, "box": [0, 0, 50, 50],
         "embedding": [1.0, 0.0, 0.0]},  # no lat/lon at all
        _det("nan", float("nan"), 77.5946),
        _det("oor", 91.0, 77.5946),
    ]
    clusters = svc.cluster_detections(dets)
    assert len(clusters) == 1  # only the valid strong solo survives
    assert clusters[0].det_ids == ["good"]
    assert "dropping 3 sighting(s)" in caplog.text


def test_gps_drift_chain_stays_one_cluster():
    """Drifted repeat sightings (8m steps, 24m span) chain into one hole."""
    svc = DeduplicatorService(CONFIG)
    emb = [1.0, 0.1, 0.0]
    dets = [_det(f"p{i}", 12.9716 + i * 8 / 111195.0, 77.5946, emb=emb)
            for i in range(4)]
    clusters = svc.cluster_detections(dets)
    assert len(clusters) == 1
    assert clusters[0].repeat_count == 4


def test_nearby_distinct_defects_stay_split():
    """Two holes 8m apart with different texture never merge."""
    svc = DeduplicatorService(CONFIG)
    dets = [_det("a", 12.97160, 77.59460, emb=[1.0, 0.0, 0.0]),
            _det("b", 12.97160 + 8 / 111195.0, 77.59460, emb=[0.0, 1.0, 0.0])]
    assert len(svc.cluster_detections(dets)) == 2


def test_repeated_sightings_compress_to_one_ticket():
    svc = DeduplicatorService(CONFIG)
    emb = [0.9, 0.1, 0.2]
    dets = [_det(f"s{i}", 12.9716 + (i % 3) * 2 / 111195.0,
                 77.5946 + (i % 2) * 2 / 111195.0, emb=emb)
            for i in range(10)]
    clusters = svc.cluster_detections(dets)
    assert len(clusters) == 1
    assert clusters[0].repeat_count == 10


def test_weak_pair_corroborates_but_stays_below_file():
    """Two weak hits at one spot corroborate into a cluster (unlike a lone
    weak hit) — but scoring keeps them out of auto-file; a person decides."""
    from agent.services.scorer import SeverityScorer

    svc = DeduplicatorService(CONFIG)
    dets = [_det("w1", 12.97160, 77.59460, conf=0.3),
            _det("w2", 12.97163, 77.59463, conf=0.4)]
    clusters = svc.cluster_detections(dets)
    assert len(clusters) == 1 and clusters[0].repeat_count == 2
    scored = SeverityScorer({"severity": {"auto_file_threshold": 70,
                                          "review_threshold": 40}}).score_cluster(clusters[0])
    assert scored.classification in ("review", "auto_dismiss")
