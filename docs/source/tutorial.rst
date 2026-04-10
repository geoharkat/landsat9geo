Tutorial: Geological Mapping
=============================

This tutorial walks through a complete geological remote-sensing workflow
using a Landsat 9 L2SP scene clipped to an area of interest.

**Inputs used:**

* ``LC09_L2SP_193036_20230713_20230715_02_T1.tar`` — Landsat 9 archive
* ``zone_polygon.shp`` — AOI polygon


1 — Full pipeline (quickest path)
----------------------------------

If you just want results on disk, the pipeline does everything in one call:

.. code-block:: python

   from landsat9geo import LandsatGeologyPipeline

   pipe = LandsatGeologyPipeline(
       tar_path="LC09_L2SP_193036_20230713_20230715_02_T1.tar",
       shp_path="zone_polygon.shp",
       output_dir="geology_output",
   )
   outputs = pipe.run()

   # outputs is a dict:
   #   "sr_30m"   → 7-band surface reflectance (cloud-masked, clipped)
   #   "st_30m"   → surface temperature in Kelvin
   #   "ratios"   → 18-band geological ratio stack

Adding optional inputs:

.. code-block:: python

   pipe = LandsatGeologyPipeline(
       tar_path="scene.tar",
       shp_path="aoi.shp",
       pan_path="B8.TIF",        # enables 15 m Brovey pansharpening
       dem_path="srtm.tif",      # enables slope / aspect / hillshade
       output_dir="results",
   )
   outputs = pipe.run()
   # now also contains "pansharpened" and "dem"


2 — Step-by-step (more control)
--------------------------------

Extract and discover files
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from landsat9geo import extract_tar, discover_files

   # From a .tar
   files = extract_tar("scene.tar", dest="extracted/")

   # Or from an already-extracted directory
   files = discover_files("extracted/")

   print(files.keys())
   # dict_keys(['SR_B1', 'SR_B2', ..., 'ST_B10', 'QA_PIXEL', 'QA_RADSAT'])


Parse metadata
^^^^^^^^^^^^^^

.. code-block:: python

   from landsat9geo import MTLParser

   meta = MTLParser("extracted/LC09_..._MTL.txt").parse()

   print(meta.landsat_id)        # LC09_L2SP_193036_...
   print(meta.acquisition_date)  # 2023-07-13
   print(meta.sun_elevation)     # 65.3
   print(meta.sr_scale)          # 0.0000275
   print(meta.st_scale)          # 0.00341802


Cloud masking
^^^^^^^^^^^^^

The QA_PIXEL band encodes cloud, shadow, cirrus, and fill flags as
individual bits.  :class:`~landsat9geo.QAMasker` extracts them:

.. code-block:: python

   import rasterio
   from landsat9geo import QAMasker

   with rasterio.open(files["QA_PIXEL"]) as src:
       qa = src.read(1)

   masker = QAMasker()
   clear = masker.cloud_mask(qa)  # True = clear sky

   # Customise which flags to include
   clear = masker.cloud_mask(
       qa,
       include_cirrus=True,      # mask cirrus (bit 2)
       include_shadow=True,      # mask cloud shadow (bit 4)
       cloud_conf_threshold=2,   # enforce high-confidence cloud flag
   )

.. note::

   The mask convention is **True = clear, False = contaminated** so you
   can use it directly as a NumPy boolean index:
   ``reflectance[~clear] = np.nan``.


Scale to reflectance
^^^^^^^^^^^^^^^^^^^^

Apply the standard USGS L2SP scaling:

   ``Surface Reflectance = DN × 0.0000275 − 0.2``   (clipped to 0–1)

   ``Thermal Kelvin = DN × 0.00341802 + 149.0``

.. code-block:: python

   import numpy as np

   with rasterio.open(files["SR_B4"]) as src:
       dn = src.read(1).astype(np.float32)

   red = np.clip(dn * meta.sr_scale + meta.sr_offset, 0.0, 1.0)
   red[~clear | (dn == 0)] = np.nan


3 — Geological indices
-----------------------

Individual functions
^^^^^^^^^^^^^^^^^^^^

Every index function takes NumPy arrays and returns a NumPy array:

.. code-block:: python

   from landsat9geo.indices import (
       iron_oxide, clay_minerals, ferrous_iron,
       carbonate, silica_index, ndvi,
   )

   fe3   = iron_oxide(red, blue)           # Red / Blue → Fe³⁺
   clay  = clay_minerals(swir1, swir2)     # SWIR1 / SWIR2 → Al-OH
   fe2   = ferrous_iron(swir1, nir)        # SWIR1 / NIR → Fe²⁺
   carb  = carbonate(swir2, nir)           # SWIR2 / NIR → CO₃²⁻
   sio2  = silica_index(swir2, swir1)      # SWIR2 / SWIR1 → quartz
   veg   = ndvi(nir, red)                  # vegetation mask

All divisions go through :func:`~landsat9geo.safe_ratio` — no
divide-by-zero surprises.


Batch computation
^^^^^^^^^^^^^^^^^

Compute all 18 ratios at once from a band dictionary:

.. code-block:: python

   from landsat9geo import compute_all_ratios

   bands = {f"SR_B{i+1}": sr_stack[i] for i in range(7)}
   ratios = compute_all_ratios(bands)

   print(list(ratios.keys()))
   # ['Iron_Oxide_R_B', 'Ferrous_Iron_S1_R', 'Clay_Hydroxyl_S1_S2',
   #  'Carbonate_S2_NIR', ... 'MVT_Carbonate_Host', 'MVT_Gossan',
   #  'MVT_Alteration_Halo']


4 — Composites
---------------

Sabins FCC
^^^^^^^^^^

The classic Sabins geological false-colour composite uses *ratio*
channels rather than raw bands:

* **R** = SWIR2 / NIR — highlights carbonates and clay
* **G** = SWIR1 / Red — ferrous iron and vegetation
* **B** = Red / Blue — iron oxides

.. code-block:: python

   from landsat9geo import sabins_fcc
   from landsat9geo.enhancement import percentile_stretch

   fcc = sabins_fcc(bands)                 # (H, W, 3) float32
   fcc_display = percentile_stretch(fcc)   # stretched to [0, 1]


MVT exploration composite
^^^^^^^^^^^^^^^^^^^^^^^^^

Targets Mississippi Valley-Type Pb-Zn deposits hosted in carbonates:

* **R** = Gossan (Red / Blue)
* **G** = Carbonate Host ((NIR + SWIR1) / SWIR2)
* **B** = Alteration Halo (SWIR1 / SWIR2)

.. code-block:: python

   from landsat9geo import mvt_target_rgb

   mvt = mvt_target_rgb(bands)


Decorrelation stretch
^^^^^^^^^^^^^^^^^^^^^

DCS removes inter-band correlation via PCA whitening, enhancing subtle
spectral differences in carbonate sequences invisible in standard FCC.
Particularly useful for MVT work in vegetated terrains.

.. code-block:: python

   from landsat9geo import decorrelation_stretch

   swir = np.stack([bands["SR_B5"], bands["SR_B6"], bands["SR_B7"]], axis=-1)
   dcs = decorrelation_stretch(swir)  # (H, W, 3) in [0, 1]


5 — Pansharpening
-------------------

Merge 30 m SR with the 15 m PAN band using the Brovey transform:

.. code-block:: python

   from landsat9geo import brovey_pansharpen
   from landsat9geo.utils import upsample_to_target

   # Upsample 30 m to 15 m grid
   sr_15m, sr_meta = upsample_to_target("SR_30m.tif", pan_meta)

   # Pansharpen
   sharpened = brovey_pansharpen(sr_15m, pan)  # (7, H, W) clipped to [0, 1]

NaN masks from cloud screening are preserved through the process — no
edge artefacts around cloud boundaries.


6 — DEM derivatives
---------------------

.. code-block:: python

   from landsat9geo import compute_dem_derivatives

   derivs = compute_dem_derivatives(
       "srtm.tif",
       target_meta=raster_profile,           # co-register to Landsat grid
       out_path="DEM_derivatives.tif",       # optional: write 4-band GeoTIFF
       sun_azimuth=meta.sun_azimuth,
       sun_altitude=meta.sun_elevation,
   )

   derivs["Elevation_m"]   # (H, W) float32
   derivs["Slope_deg"]     # Horn's method
   derivs["Aspect_deg"]    # 0 = North, clockwise
   derivs["Hillshade"]     # 0–255

If the CRS is geographic (degrees), pixel sizes are automatically
converted to metres using ``111 320 × cos(latitude_mid)``.

Drainage networks extracted from DEMs serve as proxies for structural
faults and lithological contacts.


7 — Full notebook
------------------

A complete Jupyter notebook covering all the steps above (with
visualisations) is included in the repository:

.. toctree::
   :maxdepth: 1

   ../examples/geological_mapping
