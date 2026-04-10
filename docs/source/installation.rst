Installation
============

From PyPI
---------

.. code-block:: bash

   pip install landsat9geo

This installs the core dependencies: ``numpy``, ``rasterio``, and
``geopandas``.


Optional extras
---------------

**Visualisation** (matplotlib for the example notebook):

.. code-block:: bash

   pip install "landsat9geo[viz]"

**Development** (testing and linting):

.. code-block:: bash

   pip install "landsat9geo[dev]"


From source (latest)
--------------------

.. code-block:: bash

   git clone https://github.com/geoharkat/landsat9geo.git
   cd landsat9geo
   pip install -e ".[dev,viz]"


System requirements
-------------------

* Python ≥ 3.9
* GDAL libraries (installed automatically via ``rasterio``)

On some Linux distributions you may need the GDAL development headers
first:

.. code-block:: bash

   # Debian / Ubuntu
   sudo apt install libgdal-dev

   # Fedora
   sudo dnf install gdal-devel


Verifying the installation
--------------------------

.. code-block:: python

   import landsat9geo as l9
   print(l9.__version__)     # → 0.1.0

Or from the command line:

.. code-block:: bash

   landsat9geo --help
