"""molass-library#387: molass.Testing.simulate_tiny, a fixture that runs the whole chain in seconds."""
import numpy as np
import pytest

from molass.Testing import simulate_tiny


@pytest.fixture(scope="module")
def chain():
    import molass
    molass.set_progress(False)
    ssd = simulate_tiny()
    corrected = ssd.trimmed_copy().corrected_copy()
    rg_curve = corrected.get_rg_curve()
    corrected.estimate_mapping()
    decomp = corrected.quick_decomposition(num_components=2)
    return ssd, corrected, rg_curve, decomp


def test_truth_is_attached():
    ssd = simulate_tiny(noise=0)
    species = ssd.simulation_truth.species
    assert [s.rg for s in species] == [40.0, 25.0]
    assert [s.mass for s in species] == [1.0, 0.8]
    assert ssd.xr.M.shape == (200, 80)


def test_the_five_calls_recover_the_documented_rg_values(chain):
    ssd, corrected, rg_curve, decomp = chain
    assert corrected.xr.M.shape[1] >= 70
    rgs = [float(c.compute_rg()) for c in decomp.get_xr_components()]
    assert rgs == pytest.approx([40.0, 25.0], rel=0.15)
    assert len(rg_curve.y) > 0 and np.isfinite(np.nanmedian(rg_curve.y))
