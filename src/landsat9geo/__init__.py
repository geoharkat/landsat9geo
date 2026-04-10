"""
landsat9geo — Landsat 9 L2SP geological mapping toolkit.
"""

__version__ = "0.1.0"

# ── Public API ──
from .processor import LandsatGeologyPipeline
from .parser import MTLParser, MTLMetadata, QAMasker
from .utils import safe_ratio, extract_tar, discover_files, save_tif
from .indices import (
    compute_all_ratios,
    sabins_fcc,
    mvt_target_rgb,
    ndvi,
    clay_minerals,
    iron_oxide,
    ferrous_iron,
    mvt_carbonate_host,
    mvt_gossan,
    mvt_alteration_halo,
)
from .enhancement import (
    brovey_pansharpen,
    decorrelation_stretch,
    percentile_stretch,
)
from .terrain import compute_dem_derivatives

__all__ = [
    "LandsatGeologyPipeline",
    "MTLParser",
    "MTLMetadata",
    "QAMasker",
    "safe_ratio",
    "extract_tar",
    "discover_files",
    "save_tif",
    "compute_all_ratios",
    "sabins_fcc",
    "mvt_target_rgb",
    "ndvi",
    "clay_minerals",
    "iron_oxide",
    "ferrous_iron",
    "mvt_carbonate_host",
    "mvt_gossan",
    "mvt_alteration_halo",
    "brovey_pansharpen",
    "decorrelation_stretch",
    "percentile_stretch",
    "compute_dem_derivatives",
]
