#!/usr/bin/env python3
"""Simulate a GPS track along a polyline (or pass through real GPS).

Plan ref: IMPLEMENTATION_PLAN.md Task 1.6.2.
Usage:
    python scripts/sim_gps.py --duration 60 --out eval/datasets/demo-route/gps.csv
    python scripts/sim_gps.py --duration 120 --polyline "12.9716,77.5946;12.9750,77.5980" --speed-kmh 18
Output CSV columns: t,lat,lon,speed
"""
from __future__ import annotations

import argparse
import csv
import math
import random

M_PER_DEG_LAT = 111_195.0
DEFAULT_POLYLINE = "12.9716,77.5946;12.9730,77.5960;12.9750,77.5980;12.9770,77.6000"


def _parse_polyline(raw: str) -> list[tuple[float, float]]:
    pts = []
    for pair in raw.split(";"):
        lat_s, _, lon_s = pair.partition(",")
        pts.append((float(lat_s.strip()), float(lon_s.strip())))
    if len(pts) < 2:
        raise ValueError("polyline needs at least 2 waypoints")
    return pts


def _seg_lengths(pts) -> list[float]:
    lens = []
    for (la1, lo1), (la2, lo2) in zip(pts, pts[1:]):
        dlat = (la2 - la1) * M_PER_DEG_LAT
        dlon = (lo2 - lo1) * M_PER_DEG_LAT * math.cos(math.radians((la1 + la2) / 2))
        lens.append(math.hypot(dlat, dlon))
    return lens


def sim_track(duration_s: int, polyline: str, speed_kmh: float, noise_m: float = 3.0,
              seed: int = 7) -> list[tuple[float, float, float, float]]:
    """Return [(t, lat, lon, speed)] at 1Hz along the polyline."""
    rng = random.Random(seed)
    pts = _parse_polyline(polyline)
    lens = _seg_lengths(pts)
    total_m = sum(lens)
    speed_ms = speed_kmh * 1000 / 3600
    rows = []
    for t in range(duration_s + 1):
        target = min(total_m, t * speed_ms)
        acc, lat, lon = 0.0, pts[0][0], pts[0][1]
        for (la1, lo1), (la2, lo2), seg in zip(pts, pts[1:], lens):
            if acc + seg >= target:
                frac = (target - acc) / seg if seg > 0 else 0.0
                lat, lon = la1 + frac * (la2 - la1), lo1 + frac * (lo2 - lo1)
                break
            acc += seg
        else:
            lat, lon = pts[-1]
        # +/-noise_m realism jitter
        lat += rng.uniform(-noise_m, noise_m) / M_PER_DEG_LAT
        lon += rng.uniform(-noise_m, noise_m) / (M_PER_DEG_LAT * math.cos(math.radians(lat)))
        rows.append((float(t), lat, lon, speed_kmh))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=int, required=True, help="track length in seconds")
    ap.add_argument("--out", required=True, help="output CSV path")
    ap.add_argument("--polyline", default=DEFAULT_POLYLINE)
    ap.add_argument("--speed-kmh", type=float, default=18.0)
    ap.add_argument("--noise-m", type=float, default=3.0)
    args = ap.parse_args()
    rows = sim_track(args.duration, args.polyline, args.speed_kmh, args.noise_m)
    with open(args.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t", "lat", "lon", "speed"])
        w.writerows(rows)
    print(f"wrote {len(rows)} points -> {args.out}")


if __name__ == "__main__":
    main()
