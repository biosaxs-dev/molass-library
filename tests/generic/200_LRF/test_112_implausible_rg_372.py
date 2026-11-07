"""molass-library#372: quick_decomposition warns about a component with an implausible Rg."""
import warnings

import numpy as np
import pytest

from molass.Testing import Species, continuum_species, simulate_ssd


def _continuum_ssd():
    envelope = lambda c: np.exp(-0.5 * ((c - 95.0) / 22.0) ** 2)
    return simulate_ssd(continuum_species(30.0, 25.0, 60, 140, envelope=envelope), noise=1.0, seed=1)


def _implausible_messages(records):
    return [str(r.message) for r in records if "physically implausible" in str(r.message)]


def test_a_degenerate_continuum_decomposition_warns_with_default_proportions():
    ssd = _continuum_ssd()
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        ssd.quick_decomposition(num_components=3)
    messages = _implausible_messages(rec)
    assert len(messages) == 1 and "proportions=[1]*k" in messages[0]
    assert "the data Rg is" in messages[0]


def test_equal_proportions_do_not_warn_on_the_same_data():
    ssd = _continuum_ssd()
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        ssd.quick_decomposition(num_components=3, proportions=[1]*3)
    assert _implausible_messages(rec) == []


def test_resolved_species_do_not_warn():
    species = [Species(amp=1.0, center=70, sigma=8, mass=2.0, rg=60.0), Species(amp=1.0, center=120, sigma=8, mass=2.0, rg=40.0),
               Species(amp=1.0, center=170, sigma=8, mass=1.5, rg=25.0)]
    ssd = simulate_ssd(species, noise=1.0, seed=1)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        ssd.quick_decomposition(num_components=3, proportions=[1]*3)
    assert _implausible_messages(rec) == []
