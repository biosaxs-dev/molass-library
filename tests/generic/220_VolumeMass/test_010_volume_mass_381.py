"""molass-library#381: concentration-free mass from the volume of correlation (Rambo and Tainer 2013, q cut 8/Rg after Grant 2022)."""
import warnings

import numpy as np
import pytest

from molass.Kratky import FormFactors as ff
from molass.SAXS.VolumeMass import volume_of_correlation, RT_CONSTANT

Q = np.linspace(0.005, 0.5, 990)


def test_sphere_vc_is_exact_and_the_mass_follows_the_formula():
    R = 25.0
    r = volume_of_correlation(Q, 100*ff.sphere_P(Q, R), ff.sphere_Rg(R), 100.0)
    assert r.vc == pytest.approx(277.78, rel=0.02)           # exact Vc of a sphere of R = 25 A
    assert r.qr == pytest.approx(r.vc**2/ff.sphere_Rg(R))
    assert r.mass == pytest.approx(r.qr/RT_CONSTANT/1000.0)
    assert r.mass == pytest.approx(32.5, abs=1.0)            # DATVC (ATSAS 3.1.3) gives 32.9 kDa for the same sphere with noise
    assert r.q_cut == pytest.approx(8/ff.sphere_Rg(R))
    assert r and r.reason is None


def test_vc_does_not_depend_on_the_intensity_scale():
    P = ff.gaussian_chain_P(Q, 30.0)
    a = volume_of_correlation(Q, 10*P, 30.0, 10.0)
    b = volume_of_correlation(Q, 1e5*P, 30.0, 1e5)
    assert a.vc == pytest.approx(b.vc) and a.mass == pytest.approx(b.mass)


def test_too_few_points_or_invalid_input_give_nan_with_a_reason():
    r = volume_of_correlation(Q[:10], np.ones(10), 30.0, 1.0)
    assert not r and np.isnan(r.mass) and "points" in r.reason
    for rg, i0, word in ((np.nan, 1.0, "Rg"), (30.0, -1.0, "I(0)"), (0.0, 1.0, "Rg")):
        r = volume_of_correlation(Q, np.ones(len(Q)), rg, i0)
        assert not r and word in r.reason


def test_component_mass_of_the_aldolase_peak_of_sample1():
    molass_data = pytest.importorskip("molass_data")
    from molass.DataObjects import SecSaxsData as SSD
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        corrected = SSD(molass_data.SAMPLE1).trimmed_copy().corrected_copy()
        decomp = corrected.quick_decomposition(num_components=3, rgcurve=corrected.get_rg_curve(), proportions=[1]*3)
        first, last = decomp.get_xr_components()[0], decomp.get_xr_components()[-1]
        aldolase, ovalbumin = first.get_volume_mass(), last.get_volume_mass()
    assert 120 < aldolase.mass < 160            # aldolase tetramer 158 kDa; 139 kDa in experiment 57
    assert 30 < ovalbumin.mass < 50             # ovalbumin 44 kDa; 37 kDa in experiment 57
    assert aldolase.rg > ovalbumin.rg


def test_mass_curve_follows_the_two_species_of_sample1():
    molass_data = pytest.importorskip("molass_data")
    from molass.DataObjects import SecSaxsData as SSD
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        corrected = SSD(molass_data.SAMPLE1).trimmed_copy().corrected_copy()
        curve = corrected.get_volume_mass_curve()
    assert len(curve.frames) > 30
    assert np.isfinite(curve.mass).all()
    assert np.median(curve.mass[:6]) > 100 and np.median(curve.mass[-6:]) < 60      # 134 -> 35 kDa in experiment 57
    assert curve.mass.shape == curve.rg.shape == curve.vc.shape == curve.frames.shape
