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
    "repository_url": "https://github.com/molass-saxs/molass-library",
    "use_repository_button": True,
}

html_theme = 'sphinx_book_theme'
html_static_path = ['_static']
html_logo = "_static/molamola.png"
html_favicon = "_static/molamola.png"

# Intersphinx mapping for external documentation cross-references
intersphinx_mapping = {
    "matplotlib": ("https://matplotlib.org/stable/", None),
}

