"""128-d detection embeddings for dedup.

Plan ref: IMPLEMENTATION_PLAN.md Task 2.1.2.
Default `orb` (no extra weights); `clip-tiny` dispatches to CLIP ViT-B/16
when torch+clip are installed, else raises a clear ImportError.
Requires opencv + numpy.
"""
from __future__ import annotations

import cv2
import numpy as np

EMB_DIM = 128


class DetectionEmbedder:
    def __init__(self, config: dict):
        """Select method from embedding.method ('orb' | 'clip-tiny')."""
        emb_cfg = config.get("embedding", {})
        self.method = emb_cfg.get("method", "orb")
        self.dim = emb_cfg.get("dim", EMB_DIM)
        self._orb = None
        if self.method == "orb":
            self._orb = cv2.ORB_create(nfeatures=500)
        elif self.method != "clip-tiny":
            raise ValueError(f"unknown embedding.method: {self.method!r}")

    def embed_orb(self, crop: np.ndarray) -> np.ndarray:
        """Mean-aggregated ORB descriptors, unit-norm, padded/truncated to dim.

        No keypoints (blank crop) -> zero vector (callers: cosine vs zero = 0).
        """
        gray = crop if crop.ndim == 2 else cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, desc = self._orb.detectAndCompute(gray, None)
        vec = np.zeros(self.dim, dtype=np.float32)
        if desc is None or len(desc) == 0:
            return vec
        mean = desc.astype(np.float32).mean(axis=0)  # 32-d for ORB
        n = min(self.dim, mean.shape[0])
        vec[:n] = mean[:n]
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec

    def embed_clip(self, crop: np.ndarray) -> np.ndarray:
        """CLIP ViT image embedding, first `dim` dims, L2 normalized."""
        try:
            import torch
            import clip  # openai/clip or compatible
        except ImportError as exc:
            raise ImportError("clip-tiny needs torch + clip installed") from exc
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        small = cv2.resize(rgb, (224, 224)).astype(np.float32) / 255.0
        mean = np.array([0.48145466, 0.4578275, 0.40821073], np.float32)
        std = np.array([0.26862954, 0.26130258, 0.27577711], np.float32)
        tensor = torch.from_numpy(((small - mean) / std).transpose(2, 0, 1)).unsqueeze(0).float()
        model, _ = clip.load("ViT-B/16", device="cpu")
        with torch.no_grad():
            feats = model.encode_image(tensor).float().numpy()[0]
        vec = np.zeros(self.dim, dtype=np.float32)
        vec[:] = feats[: self.dim]
        norm = float(np.linalg.norm(vec))
        return vec / norm if norm > 0 else vec

    def embed(self, crop: np.ndarray) -> np.ndarray:
        """Dispatch to the configured method."""
        if self.method == "clip-tiny":
            return self.embed_clip(crop)
        return self.embed_orb(crop)

    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Cosine similarity; 0.0 when either side is a zero vector."""
        denom = float(np.linalg.norm(emb1) * np.linalg.norm(emb2))
        if denom == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / denom)
