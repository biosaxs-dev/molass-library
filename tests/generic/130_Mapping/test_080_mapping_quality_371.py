"""molass-library#371: MappingInfo.quality and the warning for an implausible XR/UV mapping."""
import warnings

import numpy as np
import pytest

from molass.Mapping.MappingInfo import MappingInfo
from molass.Testing import Species, simulate_ssd

SPECIES = [Species(amp=1.0, center=90, sigma=8, mass=1.0, rg=25.0),
           Species(amp=1.0, center=165, sigma=8, mass=2.0, rg=40.0, na=0.3)]


def _with(m, slope, intercept):
    return MappingInfo(slope, intercept, m.xr_peaks, m.uv_peaks, None, None, m.xr_curve, m.uv_curve)


def test_a_correct_mapping_has_high_quality_and_no_warning():
    ssd = simulate_ssd(SPECIES, seed=1)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        m = ssd.estimate_mapping()
    assert m.quality.correlation > 0.9 and m.quality.coverage > 0.9
    assert m.is_plausible()
    assert "shape_correlation=" in repr(m)


def test_a_late_uv_trace_lowers_the_quality_of_the_nominal_mapping():
    ssd = simulate_ssd(SPECIES, seed=1, uv_late=40.0)
    nominal = _with(ssd.estimate_mapping(), *ssd.simulation_truth.mapping)
    right = _with(nominal, *ssd.simulation_truth.true_mapping)
    assert right.quality.correlation > 0.9
    assert nominal.quality.correlation < right.quality.correlation - 0.3


def test_the_mapping_of_ecocas3_with_molass_1_2_2_is_implausible():
    """slope 0.133 / intercept 741 instead of about 0.958 / 30: the UV curve is stretched far beyond the XR range."""
    ssd = simulate_ssd(SPECIES, seed=1)
    m = _with(ssd.estimate_mapping(), 0.133, 741.0)
    assert not m.is_plausible()
    assert m.quality.coverage < 0.3


def test_estimate_mapping_warns_about_an_implausible_mapping(monkeypatch):
    import molass.Mapping.SimpleMapper as simple_mapper
    ssd = simulate_ssd(SPECIES, seed=1)
    good = ssd.estimate_mapping()
    bad = _with(good, good.slope, good.intercept + 0.3 * good.slope * 241)
    monkeypatch.setattr(simple_mapper, "estimate_mapping_impl", lambda *args, **kwargs: bad)
    with pytest.warns(UserWarning, match="looks implausible") as rec:
        ssd.estimate_mapping()
    assert "plot_diagnostics" in str(rec[0].message)


def test_quality_is_nan_not_an_error_when_it_cannot_be_computed():
    ssd = simulate_ssd(SPECIES, seed=1)
    m = _with(ssd.estimate_mapping(), 1.0, 1e6)      # no overlap at all
    assert m.quality.coverage == 0.0 and np.isnan(m.quality.correlation)
    assert not np.isnan(m.slope)
