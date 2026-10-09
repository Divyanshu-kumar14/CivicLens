"""DBSCAN dedup combining spatial + visual similarity.

Plan ref: IMPLEMENTATION_PLAN.md Task 2.2.1.
Input detections are dicts with det_id, lat, lon, conf, embedding (array-like
or None) and box [x, y, w, h]. sklearn is imported lazily so the module loads
without the numeric stack.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field

from vision.gps import haversine_distance


@dataclass
class Cluster:
    cluster_id: str = ""
    det_ids: list[str] = field(default_factory=list)
    centroid: tuple[float, float] = (0.0, 0.0)
    repeat_count: int = 0
    representative_det_id: str = ""
    detections: list[dict] = field(default_factory=list)


def cosine_sim(a, b) -> float:
    """Cosine similarity for array-likes; 0.0 on zero vectors / Nones."""
    if a is None or b is None:
        return 0.0
    try:
        import numpy as np

        va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        return float(np.dot(va, vb) / denom) if denom > 0 else 0.0
    except ImportError:
        dot = sum(x * y for x, y in zip(a, b))
        na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na > 0 and nb > 0 else 0.0


class DeduplicatorService:
    def __init__(self, config: dict):
        """Load dedup.geo_eps_m / cos_thresh / min_samples."""
        dedup = config.get("dedup", {})
        self.geo_eps_m = dedup.get("geo_eps_m", 15)
        self.cos_thresh = dedup.get("cos_thresh", 0.82)
        self.min_samples = dedup.get("min_samples", 2)

    def _pair_cost(self, a: dict, b: dict) -> float:
        geo = haversine_distance(a["lat"], a["lon"], b["lat"], b["lon"])
        if geo > self.geo_eps_m:
            return geo  # far apart: never the same hole
        sim = cosine_sim(a.get("embedding"), b.get("embedding"))
        if sim < self.cos_thresh:
            # Close in space but visually different: push beyond eps so the
            # pair can never merge (a raw 1-sim <= 2 would always sit inside
            # a meter-scale eps and make the visual gate dead).
            return self.geo_eps_m * (2.0 - sim)
        return 0.0  # same hole

    def cluster_detections(self, detections: list[dict]) -> list[Cluster]:
        """DBSCAN over the combined metric. Noise with conf > 0.5 survives solo."""
        from sklearn.cluster import DBSCAN

        try:
            import numpy as np
        except ImportError as exc:
            raise ImportError("numpy is required for clustering") from exc

        if not detections:
            return []
        if len(detections) == 1:
            only = detections[0]
            if only.get("conf", 0) <= 0.5:
                return []  # lone weak hit dismissed
            return [self._singleton(only)]

        n = len(detections)
        dist = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                dist[i, j] = dist[j, i] = self._pair_cost(detections[i], detections[j])
        labels = DBSCAN(eps=self.geo_eps_m, min_samples=self.min_samples,
                        metric="precomputed").fit_predict(dist)

        groups: dict[int, list[dict]] = {}
        for det, label in zip(detections, labels):
            if label == -1:
                if det.get("conf", 0) > 0.5:
                    groups.setdefault(f"solo-{det.get('det_id')}", []).append(det)
                continue  # weak noise dismissed
            groups.setdefault(int(label), []).append(det)
        return [self._to_cluster(members) for members in groups.values()]

    @staticmethod
    def _to_cluster(members: list[dict]) -> Cluster:
        rep = max(members, key=lambda d: d.get("conf", 0))
        lat = sum(d["lat"] for d in members) / len(members)
        lon = sum(d["lon"] for d in members) / len(members)
        return Cluster(
            cluster_id=uuid.uuid4().hex,
            det_ids=[d.get("det_id", "") for d in members],
            centroid=(lat, lon),
            repeat_count=len(members),
            representative_det_id=rep.get("det_id", ""),
            detections=members,
        )

    def _singleton(self, det: dict) -> Cluster:
        return Cluster(
            cluster_id=uuid.uuid4().hex,
            det_ids=[det.get("det_id", "")],
            centroid=(det["lat"], det["lon"]),
            repeat_count=1,
            representative_det_id=det.get("det_id", ""),
            detections=[det],
        )

    @staticmethod
    def get_dedup_stats(raw_count: int, cluster_count: int) -> dict:
        ratio = raw_count / cluster_count if cluster_count else 0.0
        return {
            "raw": raw_count,
            "clustered": cluster_count,
            "ratio": round(ratio, 2),
            "reduction_pct": round(100 * (1 - cluster_count / raw_count), 1) if raw_count else 0.0,
        }
