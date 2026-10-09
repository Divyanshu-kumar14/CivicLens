"""Severity scoring: 0.50 area + 0.25 repeat + 0.15 route + 0.10 lane.

Plan ref: IMPLEMENTATION_PLAN.md Task 2.2.2.
Pure stdlib (geometry helpers mirror vision/classical.py without the cv2 dep
so the agent image stays lean).
"""
from __future__ import annotations

from dataclasses import dataclass

from agent.services.cluster import Cluster

REPEAT_SATURATION = 5  # 5+ passes = max repeat score
BUS_PROXIMITY_M = 50.0


@dataclass
class ScoredCluster(Cluster):
    severity: int = 0
    classification: str = ""  # auto_file | review | auto_dismiss
    signals: dict = None

    def __post_init__(self):
        if self.signals is None:
            self.signals = {}


def _perspective_area(box: list, frame_height: int = 540) -> float:
    """Mirror of vision.classical.perspective_area for [x, y, w, h] dicts/boxes."""
    x, y, w, h = (box["x"], box["y"], box["w"], box["h"]) if isinstance(box, dict) else box
    area = w * h
    depth = min(max((y + h) / max(1, frame_height), 0.0), 1.0)
    return min(max((area / max(1, frame_height) ** 2) / max(0.2, depth), 0.0), 1.0)


def _is_center_lane(box, frame_width: int = 960, lane_fraction: float = 0.6) -> bool:
    x, y, w, h = (box["x"], box["y"], box["w"], box["h"]) if isinstance(box, dict) else box
    return abs((x + w / 2.0) - frame_width / 2.0) <= frame_width * lane_fraction / 2.0


class SeverityScorer:
    def __init__(self, config: dict):
        """Load severity weights + file/review thresholds."""
        sev = config.get("severity", {})
        self.w_area = sev.get("w_area", 0.50)
        self.w_repeat = sev.get("w_repeat", 0.25)
        self.w_route = sev.get("w_route", 0.15)
        self.w_lane = sev.get("w_lane", 0.10)
        self.auto_file_threshold = sev.get("auto_file_threshold", 70)
        self.review_threshold = sev.get("review_threshold", 40)

    def score_cluster(self, cluster: Cluster, bus_routes: dict | None = None,
                      frame_width: int = 960, frame_height: int = 540) -> ScoredCluster:
        """Weighted 0-100 score from the representative detection + repeats."""
        rep = next((d for d in cluster.detections
                    if d.get("det_id") == cluster.representative_det_id),
                   cluster.detections[0])
        box = rep.get("box", [0, 0, 0, 0])
        area_norm = _perspective_area(box, frame_height) * 100
        # Strongest area across members (hole seen close-up at least once).
        for det in cluster.detections:
            area_norm = max(area_norm, _perspective_area(det.get("box", [0, 0, 0, 0]),
                                                         frame_height) * 100)

        repeat = min(cluster.repeat_count / REPEAT_SATURATION, 1.0) * 100

        bus_route_w = 0.0
        if bus_routes:
            from vision.gps import haversine_distance

            lat, lon = cluster.centroid
            for waypoints in bus_routes.values():
                if any(haversine_distance(lat, lon, wlat, wlon) <= BUS_PROXIMITY_M
                       for wlat, wlon in waypoints):
                    bus_route_w = 100.0
                    break

        center_lane = 100.0 if _is_center_lane(box, frame_width) else 30.0

        severity = round(
            self.w_area * area_norm
            + self.w_repeat * repeat
            + self.w_route * bus_route_w
            + self.w_lane * center_lane
        )
        signals = {"area_norm": round(area_norm, 1), "repeat": round(repeat, 1),
                   "bus_route_w": bus_route_w, "center_lane": center_lane}
        return ScoredCluster(
            cluster_id=cluster.cluster_id, det_ids=cluster.det_ids,
            centroid=cluster.centroid, repeat_count=cluster.repeat_count,
            representative_det_id=cluster.representative_det_id,
            detections=cluster.detections, severity=max(0, min(100, severity)),
            classification=self.classify(severity), signals=signals,
        )

    def classify(self, severity: int) -> str:
        if severity >= self.auto_file_threshold:
            return "auto_file"
        if severity >= self.review_threshold:
            return "review"
        return "auto_dismiss"
