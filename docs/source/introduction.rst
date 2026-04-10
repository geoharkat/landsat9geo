Introduction
============

**landsat9geo** is a Python package that turns raw Landsat 9 L2SP archives
into analysis-ready geological products in a single function call.

It was built by geologists, for geologists — every ratio, mask, and
composite in the package has a clear mineralogical or structural purpose.


Why Landsat 9 for geology?
--------------------------

Landsat 9 carries the OLI-2 sensor with seven reflectance bands spanning
the visible through shortwave-infrared (SWIR) spectrum, plus a thermal
channel (TIRS-2).  This spectral coverage is ideal for lithological
discrimination:

* **SWIR1 (1.57–1.65 µm)** and **SWIR2 (2.11–2.29 µm)** bracket the
  hydroxyl-ion absorption feature at ~2.2 µm, making them sensitive to
  clay minerals (kaolinite, illite, montmorillonite).
* **Red / Blue** ratios exploit the charge-transfer absorption of ferric
  iron (Fe³⁺), highlighting gossans, laterite caps, and iron-oxide
  alteration.
* **Thermal B10** detects radiometric contrasts between lithologies and
  can flag geothermal anomalies or sulphide-oxidation heat.

The Level-2 Science Product (L2SP) provides atmospherically corrected
surface reflectance and surface temperature, so you can go straight to
band-ratio analysis without manual atmospheric correction.


Key features
------------

Pipeline automation
   Extract a ``.tar`` archive, parse the MTL, build cloud/shadow masks,
   scale to reflectance, clip to an AOI shapefile, compute 18 geological
   ratios, and write compressed GeoTIFFs — all with
   :class:`~landsat9geo.LandsatGeologyPipeline`.

Safe band math
   Every division in the package passes through
   :func:`~landsat9geo.safe_ratio`, which returns ``NaN`` where the
   denominator is near zero.  No silent ``inf`` values or divide-by-zero
   warnings.

18 geological indices
   Iron oxide, clay/hydroxyl, ferrous iron, carbonate, silica, opaque
   minerals, BSI, NDVI, plus three dedicated **MVT exploration** ratios
   (Carbonate Host, Gossan, Alteration Halo).

Composite builders
   Sabins FCC, MVT target RGB, standard geology FCC — ready-to-display
   composites with correct band assignments.

Decorrelation stretch
   PCA-based DCS on SWIR bands to reveal subtle spectral differences in
   carbonate sequences that are invisible in standard false-colour images.

Brovey pansharpening
   Merge 30 m reflectance with the 15 m panchromatic band while
   preserving NaN cloud masks (no edge artefacts).

DEM derivatives
   Horn's-method slope, aspect, and hillshade — with automatic degree →
   metre conversion for geographic CRS — co-registered to the Landsat
   grid.

CLI & notebook
   A ``landsat9geo`` command-line tool and an example Jupyter notebook
   are included.


Architecture
------------

The package follows a strict modular layout:

.. list-table::
   :widths: 20 60
   :header-rows: 1

   * - Module
     - Responsibility
   * - ``parser``
     - MTL parsing (``.txt`` / ``.json`` / ``.xml``), QA bit extraction
   * - ``indices``
     - All spectral indices, MVT ratios, Sabins FCC, batch computation
   * - ``enhancement``
     - Brovey pansharpening, decorrelation stretch, percentile stretch
   * - ``terrain``
     - DEM co-registration, slope, aspect, hillshade
   * - ``utils``
     - ``safe_ratio``, tar extraction, file discovery, clipping, GeoTIFF I/O
   * - ``processor``
     - :class:`~landsat9geo.LandsatGeologyPipeline` orchestrator
   * - ``cli``
     - Command-line entry point


Band mapping reference
----------------------

.. list-table::
   :widths: 10 15 25 15
   :header-rows: 1

   * - Band
     - Name
     - Wavelength (µm)
     - Resolution
   * - B1
     - Coastal / Aerosol
     - 0.43–0.45
     - 30 m
   * - B2
     - Blue
     - 0.45–0.51
     - 30 m
   * - B3
     - Green
     - 0.53–0.59
     - 30 m
   * - B4
     - Red
     - 0.64–0.67
     - 30 m
   * - B5
     - NIR
     - 0.85–0.88
     - 30 m
   * - B6
     - SWIR1
     - 1.57–1.65
     - 30 m
   * - B7
     - SWIR2
     - 2.11–2.29
     - 30 m
   * - B8
     - PAN
     - 0.50–0.68
     - 15 m
   * - B10
     - Thermal
     - 10.6–11.2
     - 100 m (resampled 30 m)
