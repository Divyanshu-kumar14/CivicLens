"""Tests for vision/embedder.py — ORB path (CLIP needs torch, skipped)."""
import numpy as np
import pytest

from vision.embedder import DetectionEmbedder

CONFIG = {"embedding": {"dim": 128, "method": "orb"}}


@pytest.fixture()
def embedder():
    return DetectionEmbedder(CONFIG)


def _texture(seed=0, h=96, w=96):
    rng = np.random.default_rng(seed)
    return (rng.random((h, w, 3)) * 255).astype(np.uint8)


def test_embed_shape_and_norm(embedder):
    vec = embedder.embed(_texture())
    assert vec.shape == (128,)
    assert float(np.linalg.norm(vec)) == pytest.approx(1.0)


def test_blank_crop_gives_zero_vector(embedder):
    vec = embedder.embed(np.zeros((96, 96, 3), np.uint8))
    assert vec.shape == (128,)
    assert (vec == 0).all()


def test_cosine_self_is_one(embedder):
    vec = embedder.embed(_texture())
    assert DetectionEmbedder.cosine_similarity(vec, vec) == pytest.approx(1.0)


def test_cosine_zero_vector_is_zero(embedder):
    vec = embedder.embed(_texture())
    zero = np.zeros(128, np.float32)
    assert DetectionEmbedder.cosine_similarity(vec, zero) == 0.0


def test_similar_crops_score_high(embedder):
    a = _texture(seed=1)
    b = a.copy()
    b[10:20, 10:20] = 0  # small occlusion
    sim = DetectionEmbedder.cosine_similarity(embedder.embed(a), embedder.embed(b))
    assert sim > 0.9


def test_unknown_method_rejected():
    with pytest.raises(ValueError, match="unknown embedding.method"):
        DetectionEmbedder({"embedding": {"method": "sift-bow"}})
