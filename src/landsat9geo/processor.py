"""
Main orchestration: load → mask → scale → clip → pansharpen → ratios → DEM.
"""

import tempfile
import numpy as np
import rasterio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .parser import MTLParser, MTLMetadata, QAMasker, DEFAULT_SR_SCALE, DEFAULT_SR_OFFSET
from .utils import (
    SR_BANDS,
    BAND_NAMES,
    extract_tar,
    discover_files,
    ensure_same_crs,
    clip_raster,
    save_tif,
    upsample_to_target,
)
from .indices import compute_all_ratios
from .enhancement import brovey_pansharpen
from .terrain import compute_dem_derivatives


# Panchromatic scaling defaults (L1TP)
_PAN_MULT: float = 2.0e-05
_PAN_ADD: float = -0.1


class LandsatGeologyPipeline:
    """
    End-to-end Landsat 9 L2SP geological processing pipeline.

    Parameters
    ----------
    tar_path : path-like, optional
        ``.tar`` archive.  Either *tar_path* or *directory* must be given.
    directory : path-like, optional
        Already-extracted directory.
    shp_path : path-like, optional
        Shapefile / GeoPackage for clipping.
    pan_path : path-like, optional
        Panchromatic band (L1TP).  If absent, 30 m processing only.
    dem_path : path-like, optional
        DEM for terrain derivatives.
    output_dir : path-like, optional
        Output directory (created if needed).
    """

    def __init__(
        self,
        *,
        tar_path: Optional[Union[str, Path]] = None,
        directory: Optional[Union[str, Path]] = None,
        shp_path: Optional[Union[str, Path]] = None,
        pan_path: Optional[Union[str, Path]] = None,
        dem_path: Optional[Union[str, Path]] = None,
        output_dir: Union[str, Path] = "geology_output",
    ):
        self.tar_path = Path(tar_path) if tar_path else None
        self.directory = Path(directory) if directory else None
        self.shp_path = Path(shp_path) if shp_path else None
        self.pan_path = Path(pan_path) if pan_path else None
        self.dem_path = Path(dem_path) if dem_path else None
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.tar_path is None and self.directory is None:
            raise ValueError("Provide tar_path or directory.")

        # Populated by run()
        self.metadata: Optional[MTLMetadata] = None
        self.files: Dict[str, str] = {}
        self._tmpdir: Optional[str] = None

    # ── public API ──

    def run(self) -> Dict[str, str]:
        """
        Execute the full pipeline.  Returns a dict of output file paths.
        """
        outputs: Dict[str, str] = {}

        # 1. Extract / discover files
        if self.tar_path is not None:
            self._tmpdir = tempfile.mkdtemp(prefix="l9_")
            self.files = extract_tar(self.tar_path, self._tmpdir)
        else:
            self.files = discover_files(self.directory)

        # 2. Parse MTL
        self.metadata = self._find_and_parse_mtl()

        # 3. Cloud mask
        cloud_mask = self._build_cloud_mask()

        # 4. SR → reflectance
        sr_stack, sr_meta = self._process_sr(cloud_mask)

        # 5. Thermal → Kelvin
        st_stack, st_meta = self._process_thermal(cloud_mask)

        # 6. Clip to AOI
        geoms = None
        if self.shp_path is not None:
            gdf = ensure_same_crs(self.shp_path, list(self.files.values())[0])
            geoms = gdf.geometry.values

        if geoms is not None:
            sr_stack, sr_meta = clip_raster(sr_stack, sr_meta, geoms)
            if st_stack is not None:
                st_stack, st_meta = clip_raster(st_stack, st_meta, geoms)

        # Save 30 m SR
        sr_30m_path = str(self.output_dir / "SR_30m.tif")
        save_tif(sr_stack, sr_meta, sr_30m_path, BAND_NAMES)
        outputs["sr_30m"] = sr_30m_path

        # Save thermal
        if st_stack is not None:
            st_path = str(self.output_dir / "ST_30m_K.tif")
            save_tif(st_stack, st_meta, st_path, ["Thermal_K"])
            outputs["st_30m"] = st_path

        # 7. Pansharpening
        ratio_src = sr_30m_path
        if self.pan_path is not None and self.pan_path.is_file():
            pan_15m_path = self._pansharpen(sr_30m_path, geoms, sr_meta.get("crs"))
            if pan_15m_path:
                outputs["pansharpened"] = pan_15m_path
                ratio_src = pan_15m_path

        # 8. Geological ratios
        ratio_path = str(self.output_dir / "geological_ratios.tif")
        ratio_names = self._compute_ratios(ratio_src, ratio_path)
        outputs["ratios"] = ratio_path

        # 9. DEM derivatives
        if self.dem_path is not None and self.dem_path.is_file():
            with rasterio.open(ratio_src) as src:
                target_meta = src.meta.copy()
            dem_out = str(self.output_dir / "DEM_derivatives.tif")
            sun_az = self.metadata.sun_azimuth if self.metadata else 180.0
            sun_alt = self.metadata.sun_elevation if self.metadata else 45.0
            compute_dem_derivatives(
                self.dem_path,
                target_meta,
                dem_out,
                sun_azimuth=sun_az,
                sun_altitude=sun_alt,
            )
            outputs["dem"] = dem_out

        return outputs

    # ── internal steps ──

    def _find_and_parse_mtl(self) -> Optional[MTLMetadata]:
        search_dir = Path(self._tmpdir) if self._tmpdir else self.directory
        for ext in ("_MTL.txt", "_MTL.json", "_MTL.xml"):
            hits = list(search_dir.glob(f"*{ext}"))
            if hits:
                return MTLParser(str(hits[0])).parse()
        return None

    def _build_cloud_mask(self) -> np.ndarray:
        qa_path = self.files.get("QA_PIXEL")
        if qa_path is None:
            raise FileNotFoundError("QA_PIXEL band not found.")
        with rasterio.open(qa_path) as src:
            qa = src.read(1)
        masker = QAMasker()
        return masker.cloud_mask(qa)

    def _process_sr(
        self,
        cloud_mask: np.ndarray,
    ) -> Tuple[np.ndarray, dict]:
        arrays, meta = [], None
        scale = self.metadata.sr_scale if self.metadata else DEFAULT_SR_SCALE
        offset = self.metadata.sr_offset if self.metadata else DEFAULT_SR_OFFSET

        for band in SR_BANDS:
            path = self.files.get(band)
            if path is None:
                raise FileNotFoundError(f"{band} not found.")
            with rasterio.open(path) as src:
                dn = src.read(1).astype(np.float32)
                if meta is None:
                    meta = src.meta.copy()
            ref = np.clip(dn * scale + offset, 0.0, 1.0)
            ref[~cloud_mask | (dn == 0)] = np.nan
            arrays.append(ref)

        stack = np.stack(arrays, axis=0)
        meta.update(count=len(SR_BANDS), dtype="float32", nodata=np.nan)
        return stack, meta

    def _process_thermal(
        self,
        cloud_mask: np.ndarray,
    ) -> Tuple[Optional[np.ndarray], Optional[dict]]:
        path = self.files.get("ST_B10")
        if path is None:
            return None, None
        scale = self.metadata.st_scale if self.metadata else 0.00341802
        offset = self.metadata.st_offset if self.metadata else 149.0

        with rasterio.open(path) as src:
            dn = src.read(1).astype(np.float32)
            meta = src.meta.copy()
        kelvin = dn * scale + offset
        kelvin[~cloud_mask | (dn == 0)] = np.nan
        meta.update(dtype="float32", nodata=np.nan)
        return kelvin[np.newaxis], meta

    def _pansharpen(
        self,
        sr_30m_path: str,
        geoms,
        raster_crs,
    ) -> Optional[str]:
        import geopandas as gpd
        from rasterio.mask import mask as rio_mask

        with rasterio.open(self.pan_path) as src:
            pan_crs = src.crs

        if geoms is not None:
            gdf_tmp = gpd.GeoDataFrame(geometry=list(geoms), crs=raster_crs)
            if pan_crs != raster_crs:
                gdf_tmp = gdf_tmp.to_crs(pan_crs)
            with rasterio.open(self.pan_path) as src:
                pan_clip, pan_t = rio_mask(
                    src,
                    gdf_tmp.geometry.values,
                    crop=True,
                    nodata=0,
                )
                pan_meta = src.meta.copy()
            pan_meta.update(
                height=pan_clip.shape[1],
                width=pan_clip.shape[2],
                transform=pan_t,
            )
        else:
            with rasterio.open(self.pan_path) as src:
                pan_clip = src.read()
                pan_meta = src.meta.copy()

        pan = pan_clip[0].astype(np.float32)
        pan = np.clip(pan * _PAN_MULT + _PAN_ADD, 0.0, 1.0)
        pan[pan_clip[0] == 0] = np.nan

        sr_15m, sr_15m_meta = upsample_to_target(sr_30m_path, pan_meta)
        sharpened = brovey_pansharpen(sr_15m, pan)

        out_path = str(self.output_dir / "SR_pansharpened_15m.tif")
        save_tif(sharpened, sr_15m_meta, out_path, BAND_NAMES)
        return out_path

    def _compute_ratios(
        self,
        sr_path: str,
        out_path: str,
    ) -> List[str]:
        with rasterio.open(sr_path) as src:
            data = src.read().astype(np.float32)
            meta = src.meta.copy()

        bands = {f"SR_B{i + 1}": data[i] for i in range(data.shape[0])}
        ratios = compute_all_ratios(bands)
        names = list(ratios.keys())
        stack = np.stack(list(ratios.values()), axis=0)
        save_tif(stack, meta, out_path, names)
        return names
