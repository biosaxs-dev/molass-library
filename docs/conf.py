# Add the root directory to the system path
# This is necessary to import the package correctly in the Sphinx documentation.
import sys
import os
root_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root_dir)    # required to import molass
tools_dir = os.path.join(root_dir, "docs", "tools")
sys.path.insert(0, tools_dir)   # required to import tools/*.py

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Molass Library'
copyright = '2025, Molass Community'
author = 'Molass Community'

# Get version from package
from molass import get_version
release = str(get_version(toml_only=True))
version = '.'.join(release.split('.')[:2])  # X.Y from X.Y.Z

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    'sphinx_copybutton',
    'myst_parser',
    "sphinx.ext.intersphinx",  # <-- Add this line
]

# Type hints configuration
autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented'

autoclass_content = 'both'
# napoleon_google_docstring = True
# napoleon_numpy_docstring = True

templates_path = ['_templates']
exclude_patterns = [
    '_build', 'Thumbs.db', '.DS_Store',
    'source/molass.SAXS.denss*',
    'source/molass.SAXS.resources*',
]

# Customize autodoc behavior
autodoc_default_options = {
    'member-order': 'bysource',  # Order members as they appear in the source code
    'undoc-members': False,      # Include undocumented members
    'show-inheritance': False,   # Show inheritance diagrams
}

# Avoid using "package" in titles
add_module_names = False  # Removes the "molass." prefix from module names in titles

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme_options = {
    "repository_url": "https://github.com/biosaxs-dev/molass-library",
    "use_repository_button": True,
    "show_toc_level": 2,
    "navigation_depth": 4,
    "pygment_dark_style": "monokai",
}

html_theme = 'sphinx_book_theme'
html_static_path = ['_static']
html_logo = "_static/molamola.png"
html_favicon = "_static/molamola.png"

# Intersphinx mapping for external documentation cross-references
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
}

