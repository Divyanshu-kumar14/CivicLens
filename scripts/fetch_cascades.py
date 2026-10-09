#!/usr/bin/env python3
"""Fetch Haar cascade XMLs into vision/models/ (pip wheels ship an empty data dir).

Run: python scripts/fetch_cascades.py   (also runs in Dockerfile.vision)
"""
from __future__ import annotations

import os
import urllib.request

BASE = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades"
FILES = [
    "haarcascade_frontalface_default.xml",
    # NOTE: plan names haarcascade_licence_plate_rus_16stages.xml, which is not
    # in opencv master; haarcascade_russian_plate_number.xml is its upstream
    # equivalent and is what we load (blur.py references this name).
    "haarcascade_russian_plate_number.xml",
]


def main() -> None:
    dest = os.path.join(os.path.dirname(__file__), "..", "vision", "models")
    os.makedirs(dest, exist_ok=True)
    for name in FILES:
        out = os.path.join(dest, name)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            print(f"exists: {out}")
            continue
        urllib.request.urlretrieve(f"{BASE}/{name}", out)
        print(f"fetched: {out} ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    main()
