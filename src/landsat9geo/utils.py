"""
I/O helpers, tar extraction, clipping, and safe math.
"""

import os
import tarfile
import tempfile
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.mask import mask as rio_mask
import geopandas as gpd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# ── Constants ──
SR_BANDS: List[str] = ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"]
BAND_NAMES: List[str] = ["Coastal", "Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"]


def safe_ratio(a: np.ndarray, b: np.ndarray, threshold: float = 1e-6) -> np.ndarray:
    """
    Divide *a* by *b*, returning NaN wherever *b* ≈ 0 or either input is NaN.

    This is the **only** division function that should ever be used for
    band ratios anywhere in the package.
    """
    out = np.full_like(a, np.nan, dtype=np.float32)
    valid = np.isfinite(a) & np.isfinite(b) & (np.abs(b) > threshold)
    out[valid] = a[valid] / b[valid]
    return out


# ── Tar / file discovery ──

def extract_tar(tar_path: Union[str, Path],
                dest: Optional[Union[str, Path]] = None,
                extra_tags: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Extract a Landsat .tar archive and return a dict mapping band tags
    (e.g. ``"SR_B4"``, ``"QA_PIXEL"``) to their file paths on disk.

    Parameters
    ----------
    tar_path : path-like
        Path to the ``.tar`` (or ``.tar.gz``) archive.
    dest : path-like, optional
        Extraction directory.  If *None* a temporary directory is created
        (caller is responsible for cleanup).
    extra_tags : list[str], optional
        Additional filename suffixes to look for beyond the defaults.
    """
    tar_path = Path(tar_path)
    if dest is None:
        dest = Path(tempfile.mkdtemp(prefix="l9_"))
    else:
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)

    with tarfile.open(tar_path) as tar:
        tar.extractall(dest)

    targets = SR_BANDS + ["ST_B10", "QA_PIXEL", "QA_RADSAT", "QA_AEROSOL"]
    if extra_tags:
        targets += extra_tags

    files: Dict[str, str] = {}
    for f in dest.glob("*.TIF"):
        for tag in targets:
            if f.name.endswith(f"_{tag}.TIF"):
                files[tag] = str(f)
    return files


def discover_files(directory: Union[str, Path],
                   extra_tags: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Discover Landsat band files already extracted in *directory*.
    """
    directory = Path(directory)
    targets = SR_BANDS + ["ST_B10", "QA_PIXEL", "QA_RADSAT", "QA_AEROSOL"]
    if extra_tags:
        targets += extra_tags

    files: Dict[str, str] = {}
    for f in directory.glob("*.TIF"):
        for tag in targets:
            if f.name.endswith(f"_{tag}.TIF"):
                files[tag] = str(f)
    return files


# ── Clipping / reprojection ──

def ensure_same_crs(vector_path: Union[str, Path],
                    raster_path: Union[str, Path]) -> gpd.GeoDataFrame:
    """
    Read a vector file and reproject it to the raster CRS if necessary.
    **Never** reprojects the raster.
    """
    gdf = gpd.read_file(vector_path)
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs
    if gdf.crs != raster_crs:
        gdf = gdf.to_crs(raster_crs)
    return gdf


def clip_raster(stack: np.ndarray,
                meta: dict,
                geometries) -> Tuple[np.ndarray, dict]:
    """
    Clip a raster stack to vector geometries using an in-memory VRT.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        with rasterio.open(tmp_path, "w", **meta) as dst:
            dst.write(stack)
        with rasterio.open(tmp_path) as src:
            clipped, clipped_t = rio_mask(src, geometries, crop=True, nodata=np.nan)
            out_meta = src.meta.copy()
        out_meta.update(
            height=clipped.shape[1],
            width=clipped.shape[2],
            transform=clipped_t,
            compress="deflate",
        )
    finally:
        os.remove(tmp_path)
    return clipped, out_meta


def save_tif(array: np.ndarray,
             meta: dict,
             out_path: Union[str, Path],
             band_names: Optional[List[str]] = None) -> None:
    """
    Write a float32 GeoTIFF with DEFLATE compression and optional band
    descriptions.
    """
    out_path = str(out_path)
    meta = meta.copy()
    meta.update(count=array.shape[0], compress="deflate", dtype="float32", nodata=np.nan)
    with rasterio.open(out_path, "w", **meta) as dst:
        dst.write(array.astype(np.float32))
        if band_names:
            for i, n in enumerate(band_names, 1):
                dst.set_band_description(i, n)


def upsample_to_target(src_path: Union[str, Path],
                        target_meta: dict) -> Tuple[np.ndarray, dict]:
    """
    Reproject / resample a raster to match *target_meta* (CRS, transform, shape).
    """
    with rasterio.open(src_path) as src:
        nb = src.count
        dst_arr = np.empty(
            (nb, target_meta["height"], target_meta["width"]), dtype=np.float32
        )
        for i in range(1, nb + 1):
            reproject(
                source=rasterio.band(src, i),
                destination=dst_arr[i - 1],
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=target_meta["transform"],
                dst_crs=target_meta["crs"],
                resampling=Resampling.cubic,
                src_nodata=src.nodata,
                dst_nodata=np.nan,
            )
        meta = src.meta.copy()
    meta.update(
        height=target_meta["height"],
        width=target_meta["width"],
        transform=target_meta["transform"],
        crs=target_meta["crs"],
        dtype="float32",
        nodata=np.nan,
    )
    return dst_arr, meta
