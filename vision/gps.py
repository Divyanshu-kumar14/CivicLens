"""GPS CSV/SRT parsing + time-sync for the CivicLens vision pipeline.

Plan ref: IMPLEMENTATION_PLAN.md Task 1.2.2.
Pure stdlib — no numpy/cv2 — so it runs on any host (API, worker, tests).
"""
from __future__ import annotations

import csv
import math
import re
from bisect import bisect_left
from dataclasses import dataclass

EARTH_RADIUS_M = 6_371_000.0


@dataclass
class GPSPoint:
    t: float  # seconds from video start
    lat: float
    lon: float
    speed: float = 0.0
    heading: float = 0.0  # degrees 0-360, calculated


def _check_lat_lon(lat: float, lon: float, where: str) -> None:
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"{where}: latitude {lat} out of range [-90, 90]")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"{where}: longitude {lon} out of range [-180, 180]")


def parse_gps_csv(csv_path: str) -> list[GPSPoint]:
    """Parse CSV with columns t, lat, lon (+ optional speed).

    Returns points sorted by t. Missing speed defaults to 0.
    Raises ValueError on malformed rows or out-of-range coords.
    """
    points: list[GPSPoint] = []
    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"t", "lat", "lon"}
        missing = required - { (h or "").strip() for h in (reader.fieldnames or []) }
        if missing:
            raise ValueError(f"{csv_path}: missing columns {sorted(missing)}")
        for lineno, row in enumerate(reader, start=2):
            try:
                t = float(row["t"])
                lat = float(row["lat"])
                lon = float(row["lon"])
                speed_raw = (row.get("speed") or "").strip()
                speed = float(speed_raw) if speed_raw else 0.0
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{csv_path}:{lineno}: bad numeric value ({exc})") from exc
            _check_lat_lon(lat, lon, f"{csv_path}:{lineno}")
            points.append(GPSPoint(t=t, lat=lat, lon=lon, speed=speed))
    points.sort(key=lambda p: p.t)
    return points


_SRT_TS = re.compile(r"(\d+):(\d{2}):(\d{2}),(\d{3})\s*-->")
_LAT_RE = re.compile(r"lat(?:itude)?\s*[:=]?\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)
_LON_RE = re.compile(r"lon(?:g(?:itude)?)?\s*[:=]?\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)
_PAIR_RE = re.compile(r"(-?\d+\.\d+)\s*[,;]\s*(-?\d+\.\d+)")
_SPEED_RE = re.compile(r"speed\s*[:=]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


def _srt_ts_to_sec(ts: str) -> float:
    m = _SRT_TS.search(ts)
    if not m:
        raise ValueError(f"bad SRT timestamp line: {ts!r}")
    hh, mm, ss, ms = map(int, m.groups())
    return hh * 3600 + mm * 60 + ss + ms / 1000.0


def parse_gps_srt(srt_path: str) -> list[GPSPoint]:
    """Parse dashcam SRT subtitles with embedded GPS text.

    Each block contributes its start timestamp + first lat/lon found in the
    text (labeled `lat:`/`lon:` preferred, bare `lat, lon` pair as fallback).
    """
    with open(srt_path) as fh:
        content = fh.read()
    points: list[GPSPoint] = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        t = _srt_ts_to_sec(lines[1])
        text = " ".join(lines[2:])
        lat_m, lon_m = _LAT_RE.search(text), _LON_RE.search(text)
        if lat_m and lon_m:
            lat, lon = float(lat_m.group(1)), float(lon_m.group(1))
        else:
            pair = _PAIR_RE.search(text)
            if not pair:
                continue  # block without coords — skip, don't fail the file
            lat, lon = float(pair.group(1)), float(pair.group(2))
        _check_lat_lon(lat, lon, f"{srt_path}@{t:.3f}s")
        speed_m = _SPEED_RE.search(text)
        points.append(GPSPoint(t=t, lat=lat, lon=lon, speed=float(speed_m.group(1)) if speed_m else 0.0))
    points.sort(key=lambda p: p.t)
    return points


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2, degrees 0-360."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters between two GPS coords."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def interpolate_gps(gps_points: list[GPSPoint], timestamp_sec: float) -> GPSPoint:
    """Linear interpolation between the two nearest GPS points.

    Timestamps outside the track range clamp to the nearest endpoint.
    Heading is computed from prev -> next segment direction.
    """
    if not gps_points:
        raise ValueError("no GPS points to interpolate")
    pts = sorted(gps_points, key=lambda p: p.t)
    if timestamp_sec <= pts[0].t:
        first = pts[0]
        nxt = pts[1] if len(pts) > 1 else first
        return GPSPoint(
            t=timestamp_sec, lat=first.lat, lon=first.lon, speed=first.speed,
            heading=bearing_deg(first.lat, first.lon, nxt.lat, nxt.lon) if nxt is not first else 0.0,
        )
    if timestamp_sec >= pts[-1].t:
        last = pts[-1]
        prv = pts[-2] if len(pts) > 1 else last
        return GPSPoint(
            t=timestamp_sec, lat=last.lat, lon=last.lon, speed=last.speed,
            heading=bearing_deg(prv.lat, prv.lon, last.lat, last.lon) if prv is not last else 0.0,
        )
    i = bisect_left([p.t for p in pts], timestamp_sec)
    prev, nxt = pts[i - 1], pts[i]
    span = nxt.t - prev.t
    alpha = (timestamp_sec - prev.t) / span if span > 0 else 0.0
    return GPSPoint(
        t=timestamp_sec,
        lat=prev.lat + alpha * (nxt.lat - prev.lat),
        lon=prev.lon + alpha * (nxt.lon - prev.lon),
        speed=prev.speed + alpha * (nxt.speed - prev.speed),
        heading=bearing_deg(prev.lat, prev.lon, nxt.lat, nxt.lon),
    )
