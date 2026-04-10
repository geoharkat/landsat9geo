"""
Image enhancement: Brovey pansharpening, decorrelation stretch, PCA,
and percentile contrast stretching.
"""

import numpy as np

from .utils import safe_ratio


# ═══════════════════════════════════════════════════════════════
#  Brovey pansharpening
# ═══════════════════════════════════════════════════════════════


def brovey_pansharpen(sr_stack: np.ndarray, pan: np.ndarray) -> np.ndarray:
    """
    Brovey transform:  ``(Band_i / ΣBands) × PAN``

    NaN masks from cloud screening are preserved so that clouded
    pixels do not create artificial edge artefacts.

    Parameters
    ----------
    sr_stack : (N, H, W) float32
        Multi-band reflectance resampled to 15 m.
    pan : (H, W) float32
        Panchromatic band (already scaled to reflectance).

    Returns
    -------
    (N, H, W) float32 clipped to [0, 1].
    """
    band_sum = np.nansum(sr_stack, axis=0)
    band_sum[band_sum == 0] = np.nan
    out = np.empty_like(sr_stack)
    for i in range(sr_stack.shape[0]):
        out[i] = safe_ratio(sr_stack[i], band_sum) * pan
    # Propagate original NaN mask (use band 0 as reference)
    nan_mask = np.isnan(sr_stack[0])
    out[:, nan_mask] = np.nan
    return np.clip(out, 0.0, 1.0)


# ═══════════════════════════════════════════════════════════════
#  Decorrelation stretch (DCS)
# ═══════════════════════════════════════════════════════════════


def decorrelation_stretch(
    stack: np.ndarray,
    target_std: float = 1.0,
) -> np.ndarray:
    """
    Apply decorrelation stretch to a 3-band (H, W, 3) image.

    DCS removes inter-band correlation via PCA whitening, greatly
    enhancing subtle spectral differences in carbonate sequences
    that are invisible in standard FCC.  Particularly useful for
    MVT exploration in vegetated or spectrally complex terrains.

    Parameters
    ----------
    stack : (H, W, 3) float32
    target_std : float
        Standard deviation to stretch each PC to before back-rotation.

    Returns
    -------
    (H, W, 3) float32 in [0, 1].
    """
    h, w, nb = stack.shape
    assert nb == 3, "DCS requires exactly 3 bands"

    flat = stack.reshape(-1, nb).astype(np.float64)

    # Valid (non-NaN) pixels
    valid = np.all(np.isfinite(flat), axis=1)
    data = flat[valid]

    if len(data) < nb + 1:
        return stack  # not enough valid pixels

    # Stats
    mean = data.mean(axis=0)
    cov = np.cov(data, rowvar=False)

    # Eigen decomposition
    eigvals, eigvecs = np.linalg.eigh(cov)
    eigvals = np.maximum(eigvals, 1e-10)

    # Forward rotation + whitening
    centered = data - mean
    rotated = centered @ eigvecs
    std = np.sqrt(eigvals)
    whitened = rotated / std * target_std

    # Back-rotation + re-mean
    stretched = whitened @ eigvecs.T + mean

    # Write back
    out = np.full_like(flat, np.nan)
    out[valid] = stretched
    out = out.reshape(h, w, nb).astype(np.float32)

    # Normalise to [0, 1]
    for i in range(nb):
        band = out[:, :, i]
        v = band[np.isfinite(band)]
        if len(v) == 0:
            continue
        lo, hi = np.percentile(v, 2), np.percentile(v, 98)
        out[:, :, i] = np.clip((band - lo) / (hi - lo + 1e-10), 0, 1)

    return out


# ═══════════════════════════════════════════════════════════════
#  Percentile contrast stretch
# ═══════════════════════════════════════════════════════════════


def percentile_stretch(
    rgb: np.ndarray,
    low_pct: float = 2.0,
    high_pct: float = 98.0,
) -> np.ndarray:
    """
    Per-band linear percentile stretch to [0, 1].

    Parameters
    ----------
    rgb : (H, W, 3) or (H, W) float32
    """
    out = np.zeros_like(rgb, dtype=np.float32)
    if rgb.ndim == 2:
        rgb = rgb[:, :, np.newaxis]
        squeeze = True
    else:
        squeeze = False

    for i in range(rgb.shape[2]):
        band = rgb[:, :, i]
        v = band[np.isfinite(band)]
        if len(v) == 0:
            continue
        lo = np.percentile(v, low_pct)
        hi = np.percentile(v, high_pct)
        out[:, :, i] = np.clip((band - lo) / (hi - lo + 1e-10), 0, 1)

    return out.squeeze() if squeeze else out
