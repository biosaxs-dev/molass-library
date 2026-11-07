"""
molass-library#373 end to end: a known-truth analysis with species of different shapes
(sphere, rod, ellipsoid) goes through quick_decomposition and get_kratky_shape_match, and the
shape categories recover the truth.
"""
import warnings

import pytest

from molass.Testing import Species, simulate_ssd


def _shape_categories(middle_shape, middle_arg):
    species = [Species(amp=1.0, center=60, sigma=7, mass=2.0, rg=40.0, shape="sphere"),
               Species(amp=1.0, center=120, sigma=7, mass=2.0, rg=45.0, shape=middle_shape, shape_arg=middle_arg),
               Species(amp=1.0, center=180, sigma=7, mass=2.0, rg=40.0, shape="chain")]
    ssd = simulate_ssd(species, noise=1.0, seed=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        decomp = ssd.quick_decomposition(num_components=3, proportions=[1]*3)
        return decomp.get_kratky_shape_match().categories


def test_sphere_and_rod_are_told_apart():
    categories = _shape_categories("cylinder", 10)
    assert categories[0] == "compact / globular"
    assert categories[1] == "elongated / rod-like"


def test_an_ellipsoid_is_moderately_anisotropic():
    categories = _shape_categories("ellipsoid", 4)
    assert categories[0] == "compact / globular"
    assert categories[1] == "moderately anisotropic"
