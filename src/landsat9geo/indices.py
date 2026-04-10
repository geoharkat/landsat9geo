"""
Spectral indices for geological and lithological mapping.

Every ratio uses :func:`~landsat9geo.utils.safe_ratio` to avoid
divide-by-zero and propagate NaN through multi-band stacks.

Band mapping (Landsat 9 OLI-2):
    B1=Coastal  B2=Blue  B3=Green  B4=Red  B5=NIR  B6=SWIR1  B7=SWIR2
"""

from typing import Dict

import numpy as np

from .utils import safe_ratio


# ═══════════════════════════════════════════════════════════════
#  Standard geological indices
# ═══════════════════════════════════════════════════════════════


def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Normalized Difference Vegetation Index — used to mask vegetation cover."""
    return safe_ratio(nir - red, nir + red)


def ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    return safe_ratio(green - nir, green + nir)


def mndwi(green: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    """Modified NDWI — better at separating water from built-up surfaces."""
    return safe_ratio(green - swir1, green + swir1)


def bsi(swir1: np.ndarray, red: np.ndarray, nir: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """Bare Soil Index — highlights exposed geological surfaces."""
    return safe_ratio(
        (swir1 + red) - (nir + blue),
        (swir1 + red) + (nir + blue),
    )


def clay_minerals(swir1: np.ndarray, swir2: np.ndarray) -> np.ndarray:
    """SWIR1 / SWIR2 — hydroxyl-ion absorption at 2.2 µm flags clays."""
    return safe_ratio(swir1, swir2)


def iron_oxide(red: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """Red / Blue — charge-transfer absorption in Fe³⁺ minerals."""
    return safe_ratio(red, blue)


def ferrous_iron(swir1: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """SWIR1 / NIR — crystal-field absorption of Fe²⁺."""
    return safe_ratio(swir1, nir)


def ferric_oxide_ratio(red: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """Normalized ferric-iron index — suppresses topographic shadow."""
    return safe_ratio(red - blue, red + blue)


def ferric_red_green(red: np.ndarray, green: np.ndarray) -> np.ndarray:
    """Red / Green — hematite vs goethite discrimination."""
    return safe_ratio(red, green)


def silica_index(swir2: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    """SWIR2 / SWIR1 — quartz-rich lithologies."""
    return safe_ratio(swir2, swir1)


def opaque_mineral(nir: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    """(NIR − SWIR1) / (NIR + SWIR1) — sulphides & oxides."""
    return safe_ratio(nir - swir1, nir + swir1)


def mineral_ratio(swir1: np.ndarray, swir2: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """(SWIR1/SWIR2) × (SWIR1/NIR) — combined alteration proxy."""
    return safe_ratio(swir1, swir2) * safe_ratio(swir1, nir)


def carbonate(swir2: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """SWIR2 / NIR — CO₃²⁻ vibrational absorption in calcite/dolomite."""
    return safe_ratio(swir2, nir)


def alunite_kaolinite(red: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    """Red / SWIR1 — alunite / kaolinite discrimination."""
    return safe_ratio(red, swir1)


def mgoh_carbonate(
    swir2: np.ndarray, blue: np.ndarray, swir1: np.ndarray, red: np.ndarray
) -> np.ndarray:
    """(SWIR2 + Blue) / (SWIR1 + Red) — MgOH & carbonate composite."""
    return safe_ratio(swir2 + blue, swir1 + red)


# ═══════════════════════════════════════════════════════════════
#  MVT (Mississippi Valley-Type) exploration indices
# ═══════════════════════════════════════════════════════════════


def mvt_carbonate_host(nir: np.ndarray, swir1: np.ndarray, swir2: np.ndarray) -> np.ndarray:
    """
    (NIR + SWIR1) / SWIR2 — maps limestone / dolostone host rocks
    typical of MVT Pb-Zn deposits.
    """
    return safe_ratio(nir + swir1, swir2)


def mvt_gossan(red: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """Red / Blue — oxidised caps (gossans) over sulphide bodies."""
    return safe_ratio(red, blue)


def mvt_alteration_halo(swir1: np.ndarray, swir2: np.ndarray) -> np.ndarray:
    """SWIR1 / SWIR2 — argillic alteration halo (illite/sericite)."""
    return safe_ratio(swir1, swir2)


# ═══════════════════════════════════════════════════════════════
#  Composite builders
# ═══════════════════════════════════════════════════════════════


def sabins_fcc(bands: Dict[str, np.ndarray]) -> np.ndarray:
    """
    Classic Sabins geological false-colour composite:
        R = SWIR2 / NIR
        G = SWIR1 / Red
        B = Red / Blue

    Returns (H, W, 3) float32 array.
    """
    r = safe_ratio(bands["SR_B7"], bands["SR_B5"])
    g = safe_ratio(bands["SR_B6"], bands["SR_B4"])
    b = safe_ratio(bands["SR_B4"], bands["SR_B2"])
    return np.stack([r, g, b], axis=-1)


def mvt_target_rgb(bands: Dict[str, np.ndarray]) -> np.ndarray:
    """
    MVT exploration composite:
        R = Gossan  (B4/B2)
        G = Carbonate host  ((B5+B6)/B7)
        B = Alteration halo  (B6/B7)
    """
    r = mvt_gossan(bands["SR_B4"], bands["SR_B2"])
    g = mvt_carbonate_host(bands["SR_B5"], bands["SR_B6"], bands["SR_B7"])
    b = mvt_alteration_halo(bands["SR_B6"], bands["SR_B7"])
    return np.stack([r, g, b], axis=-1)


def geological_fcc_standard(bands: Dict[str, np.ndarray]) -> np.ndarray:
    """R=SWIR2, G=SWIR1, B=Red — standard geology FCC."""
    return np.stack([bands["SR_B7"], bands["SR_B6"], bands["SR_B4"]], axis=-1)


def geological_fcc_alt(bands: Dict[str, np.ndarray]) -> np.ndarray:
    """R=SWIR1, G=NIR, B=Red."""
    return np.stack([bands["SR_B6"], bands["SR_B5"], bands["SR_B4"]], axis=-1)


# ── Batch computation ──


def compute_all_ratios(bands: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """
    Compute every geological ratio from a dict of reflectance bands
    keyed ``SR_B1`` … ``SR_B7``.

    Returns a dict of name → 2-D array.
    """
    b2= bands["SR_B2"]
    b3= bands["SR_B3"]
    b4= bands["SR_B4"]
    b5= bands["SR_B5"]
    b6= bands["SR_B6"]
    b7= bands["SR_B7"]



    return {
        "Iron_Oxide_R_B": iron_oxide(b4, b2),
        "Ferrous_Iron_S1_R": ferrous_iron(b6, b4),
        "Clay_Hydroxyl_S1_S2": clay_minerals(b6, b7),
        "Carbonate_S2_NIR": carbonate(b7, b5),
        "Ferric_Oxide_R_G": ferric_red_green(b4, b3),
        "NDVI": ndvi(b5, b4),
        "Silica_S2_S1": silica_index(b7, b6),
        "Alunite_Kaol_R_S1": alunite_kaolinite(b4, b6),
        "MgOH_Carb": mgoh_carbonate(b7, b2, b6, b4),
        "Sabins_R": safe_ratio(b7, b5),
        "Sabins_G": safe_ratio(b6, b4),
        "Sabins_B": safe_ratio(b4, b2),
        "BSI": bsi(b6, b4, b5, b2),
        "Opaque_Mineral": opaque_mineral(b5, b6),
        "Mineral_Ratio": mineral_ratio(b6, b7, b5),
        "MVT_Carbonate_Host": mvt_carbonate_host(b5, b6, b7),
        "MVT_Gossan": mvt_gossan(b4, b2),
        "MVT_Alteration_Halo": mvt_alteration_halo(b6, b7),
    }
