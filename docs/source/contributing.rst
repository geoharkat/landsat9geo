Contributing
============

Contributions are welcome — bug fixes, new indices, documentation
improvements, and test cases are all appreciated.


Setting up a development environment
-------------------------------------

.. code-block:: bash

   git clone https://github.com/geoharkat/landsat9geo.git
   cd landsat9geo
   pip install -e ".[dev,viz]"
   pytest                     # run the test suite


Coding standards
----------------

* **Safe division only** — every band ratio must use
  :func:`~landsat9geo.safe_ratio`.  Never write ``a / b`` directly.
* **Type hints** on all public function signatures.
* **No hardcoded paths** — file paths are always function arguments.
* **DEFLATE compression** in all GeoTIFF outputs.
* **CRS rule** — always reproject the *vector* to the raster CRS, never
  the other way round.
* Place new features in the correct module (see
  :doc:`introduction` → Architecture).


Adding a new spectral index
---------------------------

1. Add the function to ``src/landsat9geo/indices.py`` using ``safe_ratio``.
2. Include it in ``compute_all_ratios()`` if it should be part of the
   standard batch.
3. Export it in ``__init__.py`` if it is a commonly used public function.
4. Add a test in ``tests/test_core.py``.
5. Document the geological purpose in the function docstring.


Running tests
-------------

.. code-block:: bash

   pytest -v


Submitting a pull request
-------------------------

1. Fork the repository.
2. Create a feature branch: ``git checkout -b feature/my-index``
3. Commit your changes: ``git commit -m "Add laterite index"``
4. Push: ``git push origin feature/my-index``
5. Open a Pull Request against ``main``.

Please include a short geological explanation of *why* the new
index/feature is useful.


Reporting issues
----------------

Use the `GitHub Issues <https://github.com/geoharkat/landsat9geo/issues>`__
page.  When reporting a bug, include:

* Your Python and ``landsat9geo`` version (``python --version``,
  ``python -c "import landsat9geo; print(landsat9geo.__version__)"``).
* The full traceback.
* A minimal reproducing example if possible.
