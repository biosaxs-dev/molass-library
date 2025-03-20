# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Molass Library'
copyright = '2025, The Molass Community'
author = 'The Molass Community'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

autoclass_content = 'both'
# napoleon_google_docstring = True
# napoleon_numpy_docstring = True

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme_options = {
    "repository_url": "https://github.com/freesemt/molass-library",
    "use_repository_button": True,
}

html_theme = 'sphinx_book_theme'
html_static_path = ['_static']
html_logo = "_static/molamola.png"
html_favicon = "_static/molamola.png"