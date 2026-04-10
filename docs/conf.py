# -- Path setup --------------------------------------------------------------
import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

# -- Project information -----------------------------------------------------
project = "landsat9geo"
copyright = "2026, Ismail Harkat"
author = "Ismail Harkat"
version = "0.1.0"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "myst_parser",
    "nbsphinx",
]

# Autosummary / autodoc
autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = True

# Intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "geopandas": ("https://geopandas.org/en/stable/", None),
    "rasterio": ("https://rasterio.readthedocs.io/en/stable/", None),
}

# Source suffixes
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- HTML output -------------------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 3,
    "collapse_navigation": False,
    "titles_only": False,
    "logo_only": False,
}
html_static_path = []
html_title = f"{project} {version}"

# -- nbsphinx ---------------------------------------------------------------
nbsphinx_execute = "never"
nbsphinx_allow_errors = True
nbsphinx_prolog = """
.. raw:: html

    <style>
    .nbinput .prompt, .nboutput .prompt { display: none; }
    </style>
"""

# -- ToDo extension ----------------------------------------------------------
todo_include_todos = True
