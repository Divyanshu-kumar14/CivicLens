"""Tests for agent/services/cluster.py."""
import pytest

from agent.services.cluster import DeduplicatorService, cosine_sim

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
