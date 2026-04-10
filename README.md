# landsat9geo

**Landsat 9 L2SP geological mapping toolkit** — spectral indices, MVT exploration ratios, Brovey pansharpening, decorrelation stretch, and DEM derivatives in a single `pip install`.

## Installation

```bash
pip install landsat9geo
```

## Quick start

### CLI

```bash
# From a .tar archive with shapefile clip
landsat9geo --tar LC09_L2SP_193036_20230713.tar --shp aoi.shp -o results/

# With panchromatic sharpening and DEM
landsat9geo --dir ./extracted/ --shp aoi.shp --pan B8.TIF --dem srtm.tif
```

### Python API

```python
from landsat9geo import LandsatGeologyPipeline

pipe = LandsatGeologyPipeline(
    tar_path="LC09_L2SP_193036_20230713.tar",
    shp_path="aoi.shp",
    pan_path="B8.TIF",
    dem_path="srtm.tif",
    output_dir="results",
)
outputs = pipe.run()
```

### Individual functions

```python
from landsat9geo import safe_ratio, sabins_fcc, mvt_target_rgb, decorrelation_stretch

# Sabins geological false-colour composite
fcc = sabins_fcc(bands)   # R=SWIR2/NIR  G=SWIR1/Red  B=Red/Blue

# MVT exploration composite
mvt = mvt_target_rgb(bands)

# Decorrelation stretch on SWIR bands for subtle carbonate differences
import numpy as np
swir_stack = np.stack([bands["SR_B5"], bands["SR_B6"], bands["SR_B7"]], axis=-1)
dcs = decorrelation_stretch(swir_stack)
```

## Output products

| Directory | Contents |
|-----------|----------|
| `SR_30m.tif` | 7-band surface reflectance (scaled, cloud-masked) |
| `ST_30m_K.tif` | Land surface temperature (Kelvin) |
| `SR_pansharpened_15m.tif` | Brovey-sharpened 15 m reflectance |
| `geological_ratios.tif` | 18-band stack of all indices |
| `DEM_derivatives.tif` | Elevation, slope, aspect, hillshade |

## Geological ratios (band order in `geological_ratios.tif`)

1. Iron Oxide (Red/Blue) — Fe³⁺ gossans, laterite
2. Ferrous Iron (SWIR1/Red) — Fe²⁺ mafics, chlorite
3. Clay/Hydroxyl (SWIR1/SWIR2) — Al-OH kaolinite, illite
4. Carbonate (SWIR2/NIR) — CO₃²⁻ calcite, dolomite
5. Ferric Oxide (Red/Green) — hematite/goethite
6. NDVI — vegetation mask
7. Silica (SWIR2/SWIR1) — quartz-rich lithologies
8–12. Sabins FCC components, BSI, MgOH …
13–15. Opaque Mineral, Mineral Ratio
16–18. **MVT indices** — Carbonate Host, Gossan, Alteration Halo

**QGIS tip:** load `geological_ratios.tif`, set bands 10/11/12 as RGB for the classic Sabins geology false-colour composite.

## Module layout

| Module | Responsibility |
|--------|----------------|
| `parser.py` | MTL parsing, QA bit extraction |
| `indices.py` | All spectral indices, MVT ratios, Sabins FCC |
| `enhancement.py` | Brovey pansharpening, decorrelation stretch |
| `terrain.py` | DEM derivatives (Horn's method) |
| `utils.py` | `safe_ratio`, I/O, tar extraction, clipping |
| `processor.py` | Pipeline orchestration |
| `cli.py` | Command-line interface |

## License

MIT
