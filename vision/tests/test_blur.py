"""Tests for vision/blur.py — synthetic frames, no real faces needed."""
import numpy as np
import pytest

from vision.blur import PrivacyBlur

CONFIG = {"privacy": {"blur_faces": True, "blur_plates": True}}


def _checker(h=120, w=160, sq=10):
    yy, xx = np.mgrid[0:h, 0:w]
    board = (((xx // sq) + (yy // sq)) % 2 * 255).astype(np.uint8)
    return np.stack([board] * 3, axis=-1)


def test_blank_frame_no_faces_no_crash():
    blur = PrivacyBlur(CONFIG)
    blank = np.zeros((240, 320, 3), np.uint8)
    assert blur.detect_faces(blank) == []
    out = blur.process_frame(blank)
    assert out.shape == blank.shape
    assert (out == blank).all()  # nothing to blur -> identical


def test_blur_regions_changes_target_area():
    blur = PrivacyBlur(CONFIG)
    img = _checker()
    region = [(20, 20, 40, 40)]
    out = blur.blur_regions(img, region, blur_strength=21)
    assert out.shape == img.shape
    assert not (out[20:60, 20:60] == img[20:60, 20:60]).all()  # blurred
    assert (out[0:10, 0:10] == img[0:10, 0:10]).all()  # outside untouched


def test_blur_regions_rejects_even_strength():
    with pytest.raises(ValueError, match="odd"):
        PrivacyBlur.blur_regions(_checker(), [(0, 0, 10, 10)], blur_strength=20)


def test_disabled_flags_skip_detection():
    blur = PrivacyBlur({"privacy": {"blur_faces": False, "blur_plates": False}})
    img = _checker()
    assert blur.detect_faces(img) == []
    assert blur.detect_plates(img) == []
    assert (blur.process_frame(img) == img).all()


def test_process_crop_keeps_shape():
    blur = PrivacyBlur(CONFIG)
    crop = _checker(h=60, w=80)
    assert blur.process_crop(crop).shape == crop.shape
