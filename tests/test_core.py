"""Basic tests for landsat9geo core functions."""

import numpy as np
import pytest


def test_safe_ratio_basic():
    from landsat9geo.utils import safe_ratio

    a = np.array([1.0, 2.0, 3.0, np.nan], dtype=np.float32)
    b = np.array([2.0, 0.0, 3.0, 1.0], dtype=np.float32)
    r = safe_ratio(a, b)
    assert r[0] == pytest.approx(0.5)
    assert np.isnan(r[1])  # div by ~0
    assert r[2] == pytest.approx(1.0)
    assert np.isnan(r[3])  # NaN input


def test_safe_ratio_all_zero():
    from landsat9geo.utils import safe_ratio

    a = np.zeros(5, dtype=np.float32)
    b = np.zeros(5, dtype=np.float32)
    r = safe_ratio(a, b)
    assert np.all(np.isnan(r))


def test_ndvi_range():
    from landsat9geo.indices import ndvi

    nir = np.array([0.4, 0.1, 0.0], dtype=np.float32)
    red = np.array([0.1, 0.4, 0.0], dtype=np.float32)
    v = ndvi(nir, red)
    assert v[0] > 0  # vegetation-like
    assert v[1] < 0  # inverted


def test_qa_cloud_mask():
    from landsat9geo.parser import QAMasker

    masker = QAMasker()
    # Bit 3 set = cloud
    qa = np.array([0, 1 << 3, 0], dtype=np.uint16)
    mask = masker.cloud_mask(qa)
    assert mask[0] is np.True_
    assert mask[1] is np.False_


def test_sabins_fcc_shape():
    from landsat9geo.indices import sabins_fcc

    bands = {f"SR_B{i}": np.random.rand(10, 10).astype(np.float32) for i in range(1, 8)}
    fcc = sabins_fcc(bands)
    assert fcc.shape == (10, 10, 3)


def test_decorrelation_stretch():
    from landsat9geo.enhancement import decorrelation_stretch

    img = np.random.rand(20, 20, 3).astype(np.float32)
    out = decorrelation_stretch(img)
    assert out.shape == img.shape
    assert np.all(out[np.isfinite(out)] >= 0)
    assert np.all(out[np.isfinite(out)] <= 1)
