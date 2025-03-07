from pathlib import Path

import setuptools

VERSION = "0.0.0"  # PEP-440

NAME = "molass"

INSTALL_REQUIRES = [
    "numpy",
    "matplotlib",
]

setuptools.setup(
    name=NAME,
    version=VERSION,
    description="Matrix Optimization with Low-rank factorization for Automated analysis of SEC-SAXS.",
    url="https://github.com/freesemt/molass-library",
    project_urls={
        "Source Code": "https://github.com/freesemt/molass-library",
    },
    author="Masatsuyo Takahashi, Nobutaka Shimizu",
    author_email="freesemt@gmail.com",
    license="GPLv3",
    classifiers=[
        "Development Status :: 1 - Planning",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3.12",
    ],
    # SAngler uses Python 3.9
    python_requires=">=3.9",
    # Requirements
    install_requires=INSTALL_REQUIRES,
    packages=["molass"],
    long_description=Path("README.md").read_text(),
    long_description_content_type="text/markdown",
)
