"""
MTL metadata parsing and QA-pixel bit extraction for Landsat 9 L2SP.
"""

import json
import re
import numpy as np
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# ── Default L2SP scaling (USGS Collection 2) ──
DEFAULT_SR_SCALE: float = 0.0000275
DEFAULT_SR_OFFSET: float = -0.2
DEFAULT_ST_SCALE: float = 0.00341802
DEFAULT_ST_OFFSET: float = 149.0


@dataclass
class MTLMetadata:
    """Parsed MTL fields relevant to geological processing."""

    landsat_id: str = ""
    acquisition_date: str = ""
    sun_elevation: float = 45.0
    sun_azimuth: float = 180.0
    path: int = 0
    row: int = 0
    sr_scale: float = DEFAULT_SR_SCALE
    sr_offset: float = DEFAULT_SR_OFFSET
    st_scale: float = DEFAULT_ST_SCALE
    st_offset: float = DEFAULT_ST_OFFSET
    crs_epsg: Optional[int] = None
    raw: Dict = field(default_factory=dict)


class MTLParser:
    """
    Parse Landsat MTL files (``.txt``, ``.json``, ``.xml``).

    Usage::

        meta = MTLParser("/path/to/LC09_..._MTL.txt").parse()
    """

    def __init__(self, mtl_path: str):
        self.mtl_path = Path(mtl_path)
        self._raw: Dict[str, str] = {}

    # ── public ──

    def parse(self) -> MTLMetadata:
        ext = self.mtl_path.suffix.lower()
        if ext == ".txt":
            self._parse_txt()
        elif ext == ".json":
            self._parse_json()
        elif ext == ".xml":
            self._parse_xml()
        else:
            raise ValueError(f"Unsupported MTL format: {ext}")
        return self._build_metadata()

    # ── private readers ──

    def _parse_txt(self) -> None:
        content = self.mtl_path.read_text()
        pattern = r'(\w+)\s*=\s*"([^"]*)"|(\w+)\s*=\s*(\S+)'
        for m in re.finditer(pattern, content):
            key = m.group(1) or m.group(3)
            val = m.group(2) or m.group(4)
            self._raw[key] = val

    def _parse_json(self) -> None:
        data = json.loads(self.mtl_path.read_text())
        self._raw = self._flatten(data)

    def _parse_xml(self) -> None:
        content = self.mtl_path.read_text()
        for key, val in re.findall(r"<(\w+)>([^<]+)</\1>", content):
            self._raw[key] = val.strip()

    # ── helpers ──

    @staticmethod
    def _flatten(d: dict, parent: str = "", sep: str = "_") -> dict:
        items: list = []
        for k, v in d.items():
            nk = f"{parent}{sep}{k}" if parent else k
            if isinstance(v, dict):
                items.extend(MTLParser._flatten(v, nk, sep).items())
            else:
                items.append((nk, v))
        return dict(items)

    def _get(self, *keys: str, default: str = "") -> str:
        for k in keys:
            if k in self._raw:
                return self._raw[k]
            for rk, rv in self._raw.items():
                if rk.upper() == k.upper():
                    return str(rv)
        return default

    def _build_metadata(self) -> MTLMetadata:
        m = MTLMetadata(raw=self._raw)
        m.landsat_id = self._get("LANDSAT_PRODUCT_ID", "LANDSAT_SCENE_ID")
        m.acquisition_date = self._get("DATE_ACQUIRED", "ACQUISITION_DATE")
        m.sun_elevation = float(self._get("SUN_ELEVATION", default="45"))
        m.sun_azimuth = float(self._get("SUN_AZIMUTH", default="180"))
        m.path = int(self._get("WRS_PATH", default="0"))
        m.row = int(self._get("WRS_ROW", default="0"))

        # SR scale — try MTL keys, fall back to USGS defaults
        sr_s = self._get("REFLECTANCE_MULT_BAND_4", "SR_B4_SCALE_FACTOR")
        if sr_s:
            m.sr_scale = float(sr_s)
        sr_o = self._get("REFLECTANCE_ADD_BAND_4", "SR_B4_ADD_OFFSET")
        if sr_o:
            m.sr_offset = float(sr_o)

        # ST scale
        st_s = self._get("ST_B10_SCALE_FACTOR", "TEMPERATURE_MULT_BAND_ST_B10")
        if st_s:
            m.st_scale = float(st_s)
        st_o = self._get("ST_B10_ADD_OFFSET", "TEMPERATURE_ADD_BAND_ST_B10")
        if st_o:
            m.st_offset = float(st_o)

        return m


# ═══════════════════════════════════════════════════════════════
#  QA bit masking
# ═══════════════════════════════════════════════════════════════

class QAMasker:
    """
    Bitwise QA_PIXEL / QA_RADSAT interpreter for Landsat 9 Collection 2.

    The cloud mask returns **True = clear, False = contaminated**.
    """

    @staticmethod
    def _bits(arr: np.ndarray, start: int, end: int) -> np.ndarray:
        n = end - start + 1
        return (arr >> start) & ((1 << n) - 1)

    def cloud_mask(
        self,
        qa_pixel: np.ndarray,
        *,
        include_cirrus: bool = True,
        include_shadow: bool = True,
        cloud_conf_threshold: int = 2,
    ) -> np.ndarray:
        """
        Build a boolean clear-sky mask from QA_PIXEL.

        Bits masked: fill (0), dilated cloud (1), cloud (3),
        optionally cirrus (2) and cloud shadow (4).
        High-confidence cloud flags (bits 8-9) are enforced at
        *cloud_conf_threshold*.
        """
        ok = np.ones_like(qa_pixel, dtype=bool)

        # Fill, dilated cloud, cloud
        ok[self._bits(qa_pixel, 0, 0) == 1] = False
        ok[self._bits(qa_pixel, 1, 1) == 1] = False
        ok[self._bits(qa_pixel, 3, 3) == 1] = False

        # Cloud confidence
        ok[self._bits(qa_pixel, 8, 9) >= cloud_conf_threshold] = False

        if include_cirrus:
            ok[self._bits(qa_pixel, 2, 2) == 1] = False
            ok[self._bits(qa_pixel, 14, 15) >= 2] = False

        if include_shadow:
            ok[self._bits(qa_pixel, 4, 4) == 1] = False

        return ok

    def saturation_mask(
        self,
        qa_radsat: np.ndarray,
        bands: Optional[List[int]] = None,
    ) -> np.ndarray:
        """True = not saturated."""
        if bands is None:
            bands = list(range(1, 8))
        ok = np.ones_like(qa_radsat, dtype=bool)
        for b in bands:
            bit = b - 1  # band 1 → bit 0
            ok[self._bits(qa_radsat, bit, bit) == 1] = False
        return ok

    def water_mask(self, qa_pixel: np.ndarray) -> np.ndarray:
        """True = water."""
        return self._bits(qa_pixel, 7, 7) == 1
