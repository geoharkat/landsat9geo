Command-Line Interface
======================

``landsat9geo`` installs a CLI entry point that runs the full pipeline
from a terminal.

Usage
-----

.. code-block:: text

   landsat9geo {--tar FILE | --dir PATH} [options]

Required (one of):

``--tar FILE``
   Path to a Landsat 9 L2SP ``.tar`` archive.

``--dir PATH``
   Path to an already-extracted L2SP directory.

Options:

``--shp FILE``
   Shapefile or GeoPackage for AOI clipping.

``--pan FILE``
   Panchromatic band (15 m) to enable Brovey pansharpening.

``--dem FILE``
   DEM raster for slope / aspect / hillshade derivatives.

``-o, --output DIR``
   Output directory (default: ``geology_output``).


Examples
--------

Minimal — extract, mask, scale, compute ratios:

.. code-block:: bash

   landsat9geo --tar LC09_L2SP_193036_20230713_20230715_02_T1.tar \
               --shp zone_polygon.shp

With pansharpening and DEM:

.. code-block:: bash

   landsat9geo --dir ./extracted/ \
               --shp aoi.shp \
               --pan LC09_B8.TIF \
               --dem srtm30.tif \
               -o results/


Output files
------------

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - File
     - Description
   * - ``SR_30m.tif``
     - 7-band surface reflectance (cloud-masked, clipped, DEFLATE)
   * - ``ST_30m_K.tif``
     - Surface temperature in Kelvin
   * - ``SR_pansharpened_15m.tif``
     - Brovey-sharpened 15 m reflectance (if ``--pan`` given)
   * - ``geological_ratios.tif``
     - 18-band stack — all spectral indices with band descriptions
   * - ``DEM_derivatives.tif``
     - 4-band stack: elevation, slope, aspect, hillshade (if ``--dem`` given)
