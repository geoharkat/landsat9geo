Changelog
=========

0.2.0 (2026-09-15)
-------------

* Initial release.
* 18 geological spectral indices (including 3 MVT-specific ratios).
* Sabins FCC and MVT target RGB composite builders.
* Decorrelation stretch (PCA-based DCS).
* Brovey pansharpening with NaN-mask preservation.
* DEM derivatives (slope, aspect, hillshade) via Horn's method.
* QA_PIXEL / QA_RADSAT cloud, shadow, cirrus, and saturation masking.
* MTL parser supporting ``.txt``, ``.json``, and ``.xml`` formats.
* ``LandsatGeologyPipeline`` end-to-end orchestrator.
* ``landsat9geo`` CLI entry point.
* Example Jupyter notebook.
