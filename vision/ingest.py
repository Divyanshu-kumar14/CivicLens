"""Video decode + frame extraction for the CivicLens vision pipeline.

Plan ref: IMPLEMENTATION_PLAN.md Task 1.2.1.
Heavy deps (opencv) are imported lazily inside functions so this module
is importable in environments without CV libraries (tests, API hosts).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:  # pragma: no cover
    import numpy as np

# 2GB upload/processing limit per plan §1.2.1.
MAX_VIDEO_BYTES = 2 * 1024**3

# Accepted H264 fourccs (compared upper-cased).
H264_FOURCCS = {"AVC1", "H264", "X264"}


@dataclass
class Frame:
    """Single sampled video frame."""

    image: np.ndarray  # BGR HxWx3
    frame_idx: int
    timestamp_sec: float
    source_path: str = ""


def _require_cv2():  # pragma: no cover - needs opencv installed
    try:
        import cv2

        return cv2
    except ImportError as exc:
        raise ImportError(
            "opencv (opencv-contrib-python-headless) is required for video ingest. "
            "Install vision/requirements.txt"
        ) from exc


def _check_size(video_path: str) -> int:
    size = os.path.getsize(video_path)
    if size > MAX_VIDEO_BYTES:
        raise ValueError("Video exceeds 2GB limit")
    return size


def _fourcc_to_str(code: int) -> str:
    return bytes((code & 0xFF, (code >> 8) & 0xFF, (code >> 16) & 0xFF, (code >> 24) & 0xFF)).decode(
        "ascii", errors="ignore"
    )


def validate_video(video_path: str) -> dict:
    """Return {duration_sec, fps, width, height, codec, size_bytes, num_frames}.

    Raise ValueError if the file is not h264 or exceeds 2GB.
    """
    cv2 = _require_cv2()
    size_bytes = _check_size(video_path)

    cap = cv2.VideoCapture(video_path)
    try:
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps != fps:  # 0 or NaN
            raise ValueError(f"Unreadable framerate: {video_path}")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        codec = _fourcc_to_str(int(cap.get(cv2.CAP_PROP_FOURCC))).strip("\x00 ").upper()
        if codec not in H264_FOURCCS:
            raise ValueError(f"Unsupported codec '{codec}': H264 required ({video_path})")
        return {
            "duration_sec": num_frames / fps if fps else 0.0,
            "fps": fps,
            "width": width,
            "height": height,
            "codec": codec,
            "size_bytes": size_bytes,
            "num_frames": num_frames,
        }
    finally:
        cap.release()


def decode_video(video_path: str, sample_fps: float = 2.0) -> Generator[Frame, None, None]:
    """Yield every Nth frame so output rate ~= sample_fps.

    timestamp_sec is derived from source fps (frame_idx / src_fps).
    """
    cv2 = _require_cv2()
    _check_size(video_path)

    cap = cv2.VideoCapture(video_path)
    try:
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        src_fps = cap.get(cv2.CAP_PROP_FPS)
        if not src_fps or src_fps != src_fps:
            raise ValueError(f"Unreadable framerate: {video_path}")
        interval = max(1, int(round(src_fps / sample_fps)))
        idx = 0
        while True:
            ok, img = cap.read()
            if not ok:
                break
            if idx % interval == 0:
                yield Frame(
                    image=img,
                    frame_idx=idx,
                    timestamp_sec=idx / src_fps,
                    source_path=video_path,
                )
            idx += 1
    finally:
        cap.release()
