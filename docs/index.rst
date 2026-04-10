.. landsat9geo documentation master file

==============================
landsat9geo |version|
==============================

.. image:: https://img.shields.io/pypi/v/landsat9geo.svg
   :target: https://pypi.org/project/landsat9geo/
.. image:: https://img.shields.io/pypi/pyversions/landsat9geo.svg
.. image:: https://img.shields.io/github/license/geoharkat/landsat9geo.svg

A **production-ready Python toolkit** for geological mapping with
Landsat 9 Level-2 Science Products (L2SP).

.. code-block:: python

   from landsat9geo import LandsatGeologyPipeline

   pipe = LandsatGeologyPipeline(
       tar_path="LC09_L2SP_193036_20230713.tar",
       shp_path="aoi.shp",
   )
   outputs = pipe.run()   # → SR, thermal, 18 ratios, all clipped & masked

----

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   introduction
   installation

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   tutorial
   cli

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api/modules

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing
   changelog


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
