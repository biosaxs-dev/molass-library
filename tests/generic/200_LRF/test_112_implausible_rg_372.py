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


class _Component:
    def __init__(self, rg):
        self.rg = rg

    def get_guinier_object(self):
        return type("Guinier", (), {"Rg": self.rg})()


class _Decomposition:
    xr_icurve = None

    def __init__(self, rgs):
        self.rgs = rgs

    def get_xr_components(self):
        return [_Component(rg) for rg in self.rgs]


def _warnings_for(monkeypatch, rgs, span=(27.0, 30.0)):
    from molass.LowRank import QuickImplement
    monkeypatch.setattr(QuickImplement, "data_rg_range", lambda ssd, icurve: span)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        QuickImplement.warn_on_implausible_component_rg(None, _Decomposition(rgs))
    return _implausible_messages(rec)


# The greedy peak recognition of the simulated continuum differs between machines (Rg 35.8 / 7.0 / 17.6 where the
# issue was found, 32.3 / 30.3 / 16.8 on another), so the warning is tested on the Rg values themselves.
def test_a_component_far_outside_the_data_rg_warns(monkeypatch):
    messages = _warnings_for(monkeypatch, [35.8, 7.0, 17.6])
    assert len(messages) == 1 and "proportions=[1]*k" in messages[0]
    assert "component(s) 2 (Rg=7.0)" in messages[0] and "the data Rg is 27-30" in messages[0]


def test_a_component_without_guinier_rg_warns(monkeypatch):
    messages = _warnings_for(monkeypatch, [30.0, float("nan"), 28.0])
    assert len(messages) == 1 and "2 (no Guinier Rg)" in messages[0]


def test_components_within_half_to_double_the_data_rg_do_not_warn(monkeypatch):
    assert _warnings_for(monkeypatch, [32.3, 30.3, 16.8]) == []


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
