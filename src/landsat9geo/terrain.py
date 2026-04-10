"""
DEM derivatives: slope, aspect, hillshade (Horn's method).

If the CRS is geographic (degrees), pixel sizes are automatically
converted to metres using ``111 320 × cos(lat_mid)``.
Drainage networks are intended as proxies for structural faults and
lithological contacts.
"""

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from .utils import save_tif


def _pixel_size_m(meta: dict) -> Tuple[float, float]:
    """Return (dx_m, dy_m) — pixel size in metres."""
    dx = abs(meta["transform"].a)
    dy = abs(meta["transform"].e)
    crs = meta.get("crs")
    if crs and crs.is_geographic:
        lat_mid = (
            meta["transform"].f
            + meta["transform"].f + dy * meta["height"]
        ) / 2.0
        m = 111320.0 * np.cos(np.radians(lat_mid))
        return dx * m, dy * m
    return dx, dy


def coregister_dem(
    dem_path: Union[str, Path],
    target_meta: dict,
) -> np.ndarray:
    """
    Reproject / resample a DEM to match the target raster grid.

    Returns
    -------
    (H, W) float32 elevation array.
    """
    with rasterio.open(dem_path) as src:
        elev = np.empty(
            (target_meta["height"], target_meta["width"]), dtype=np.float32
        )
        reproject(
            source=rasterio.band(src, 1),
            destination=elev,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=target_meta["transform"],
            dst_crs=target_meta["crs"],
            resampling=Resampling.cubic,
            src_nodata=src.nodata,
            dst_nodata=np.nan,
        )
    return elev


def slope_aspect(
    elev: np.ndarray,
    dx_m: float,
    dy_m: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Horn's method gradient → slope (degrees) and aspect (degrees, 0=N CW).
    """
    p = np.pad(elev, 1, mode="edge")
    dzdx = (
        (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:])
        - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])
    ) / (8 * dx_m)
    dzdy = (
        (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])
        - (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:])
    ) / (8 * dy_m)

    slp = np.degrees(np.arctan(np.sqrt(dzdx ** 2 + dzdy ** 2)))
    asp = np.degrees(np.arctan2(-dzdx, dzdy))
    asp[asp < 0] += 360.0

    nan = np.isnan(elev)
    slp[nan] = np.nan
    asp[nan] = np.nan
    return slp, asp


def hillshade(
    slope_deg: np.ndarray,
    aspect_deg: np.ndarray,
    sun_azimuth: float = 180.0,
    sun_altitude: float = 45.0,
) -> np.ndarray:
    """
    Analytical hillshade (0-255 scale).
    """
    az = np.radians(sun_azimuth)
    alt = np.radians(sun_altitude)
    slp = np.radians(slope_deg)
    asp = np.radians(aspect_deg)
    hs = np.sin(alt) * np.cos(slp) + np.cos(alt) * np.sin(slp) * np.cos(az - asp)
    hs = np.clip(hs * 255, 0, 255)
    hs[np.isnan(slope_deg)] = np.nan
    return hs


def compute_dem_derivatives(
    dem_path: Union[str, Path],
    target_meta: dict,
    out_path: Optional[Union[str, Path]] = None,
    sun_azimuth: float = 180.0,
    sun_altitude: float = 45.0,
) -> Dict[str, np.ndarray]:
    """
    Full DEM processing pipeline:
    coregister → elevation, slope, aspect, hillshade.

    If *out_path* is given the 4-band stack is written as a GeoTIFF.
    """
    elev = coregister_dem(dem_path, target_meta)
    dx_m, dy_m = _pixel_size_m(target_meta)
    slp, asp = slope_aspect(elev, dx_m, dy_m)
    hs = hillshade(slp, asp, sun_azimuth, sun_altitude)

    result = {
        "Elevation_m": elev,
        "Slope_deg": slp,
        "Aspect_deg": asp,
        "Hillshade": hs,
    }

    if out_path is not None:
        stack = np.stack(list(result.values()), axis=0)
        save_tif(stack, target_meta, out_path, list(result.keys()))

    return result
