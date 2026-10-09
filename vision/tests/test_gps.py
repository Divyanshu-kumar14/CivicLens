"""Tests for vision/gps.py — pure stdlib, no CV deps needed."""
import math

import pytest

from vision.gps import (
    GPSPoint,
    bearing_deg,
    haversine_distance,
    interpolate_gps,
    parse_gps_csv,
    parse_gps_srt,
)


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return str(p)


def test_parse_csv_valid(tmp_path):
    csv_path = _write(
        tmp_path, "track.csv",
        "t,lat,lon,speed\n"
        "0,12.9716,77.5946,5.0\n"
        "1,12.9717,77.5947,5.5\n"
        "2,12.9718,77.5948,\n"  # missing speed -> 0
        "3,12.9719,77.5949,6.0\n"
        "4,12.9720,77.5950,6.5\n",
    )
    pts = parse_gps_csv(csv_path)
    assert len(pts) == 5
    assert [p.t for p in pts] == [0, 1, 2, 3, 4]
    assert pts[2].speed == 0.0
    assert pts[0].lat == pytest.approx(12.9716)


def test_parse_csv_rejects_bad_lat(tmp_path):
    csv_path = _write(tmp_path, "bad.csv", "t,lat,lon\n0,91.0,77.5\n")
    with pytest.raises(ValueError, match="latitude"):
        parse_gps_csv(csv_path)


def test_interpolate_midpoint():
    pts = [GPSPoint(t=0, lat=10.0, lon=20.0), GPSPoint(t=10, lat=11.0, lon=22.0)]
    mid = interpolate_gps(pts, 5.0)
    assert mid.lat == pytest.approx(10.5)
    assert mid.lon == pytest.approx(21.0)
    assert 0.0 <= mid.heading <= 360.0


def test_interpolate_clamps_outside():
    pts = [GPSPoint(t=0, lat=10.0, lon=20.0), GPSPoint(t=10, lat=11.0, lon=22.0)]
    before = interpolate_gps(pts, -5.0)
    after = interpolate_gps(pts, 99.0)
    assert (before.lat, before.lon) == (10.0, 20.0)
    assert (after.lat, after.lon) == (11.0, 22.0)


def test_haversine_known_distance():
    # 1 degree of latitude at the equator ~= 111.195 km (within 1%).
    d = haversine_distance(0.0, 0.0, 1.0, 0.0)
    assert d == pytest.approx(111_195, rel=0.01)
    assert haversine_distance(12.9, 77.5, 12.9, 77.5) == pytest.approx(0.0)


def test_bearing_cardinal():
    assert bearing_deg(0.0, 0.0, 1.0, 0.0) == pytest.approx(0.0)    # north
    assert bearing_deg(0.0, 0.0, 0.0, 1.0) == pytest.approx(90.0)   # east


def test_parse_srt_basic(tmp_path):
    srt_path = _write(
        tmp_path, "dash.srt",
        "1\n00:00:00,000 --> 00:00:01,000\nlat: 12.9716 lon: 77.5946 speed: 5.0\n\n"
        "2\n00:00:01,000 --> 00:00:02,000\n12.9717, 77.5947\n",
    )
    pts = parse_gps_srt(srt_path)
    assert len(pts) == 2
    assert pts[0].t == pytest.approx(0.0)
    assert pts[1].t == pytest.approx(1.0)
    assert pts[0].speed == pytest.approx(5.0)
    assert pts[1].lat == pytest.approx(12.9717)
