"""
molass-library#374 and #377 end to end: the continuity report without the shape library, and the Rg
helpers of Decomposition, on a simulated decomposition with a known truth (three resolved spheres).
"""
import numpy as np
import pytest

import molass
from molass.Testing import Species, simulate_ssd
from molass.Kratky import ShapeMatch

CENTRES = (70, 120, 170)


@pytest.fixture(scope="module")
def decomposition():
    species = [Species(amp=1.0, center=70, sigma=8, mass=2.0, rg=60.0), Species(amp=1.0, center=120, sigma=8, mass=2.0, rg=40.0),
               Species(amp=1.0, center=170, sigma=8, mass=1.5, rg=25.0)]
    ssd = simulate_ssd(species, noise=1.0, seed=1)
    rgcurve = ssd.get_rg_curve()
    return ssd.quick_decomposition(num_components=3, rgcurve=rgcurve, proportions=[1]*3), rgcurve


def test_get_reliable_rg_is_the_filtered_and_sorted_data_rg_curve(decomposition):
    decomp, rgcurve = decomposition
    frames, rgs = decomp.get_reliable_rg(rgcurve=rgcurve)
    assert len(frames) == len(rgs) > 50 and np.all(np.diff(frames) > 0)
    assert np.all((rgs > 0) & (rgs < 99))
    strict_frames, _ = decomp.get_reliable_rg(score_min=0.9, intensity_frac=0.3, rgcurve=rgcurve)
    assert 0 < len(strict_frames) < len(frames)                      # the arguments filter more


def test_component_extents_sit_on_the_elution_peaks(decomposition):
    decomp, _ = decomposition
    extents = decomp.get_component_extents()
    assert len(extents) == 3
    for (mean, sd), centre in zip(extents, CENTRES):
        assert abs(mean - centre) < 10 and 3 < sd < 20


def test_the_default_report_does_not_build_the_shape_library(decomposition, monkeypatch):
    decomp, rgcurve = decomposition

    def forbidden(*args, **kwargs):
        raise AssertionError("the shape library must not be built for the continuity report")

    monkeypatch.setattr(ShapeMatch, "_prime_reference_curves", forbidden)
    assert getattr(decomp, "_kratky_shape_match", None) is None
    report = decomp.get_continuity_report(rgcurve=rgcurve)
    assert report.verdict == "discrete" and report.best_shapes is None
    assert report.max_separation >= 0 and len(report.kratky_curves) == 3
    assert "best library shapes" not in repr(report)


def test_shapes_true_adds_the_best_shapes_and_the_same_curves(decomposition, tmp_path, monkeypatch):
    decomp, rgcurve = decomposition
    # a fresh in-memory cache, whatever earlier tests of the process have already primed
    monkeypatch.setattr(ShapeMatch, "_PRIMED_REFERENCE_CURVES", {})
    try:
        molass.set_cache_dir(tmp_path)                               # the library curves are cached here
        report = decomp.get_continuity_report(rgcurve=rgcurve, shapes=True)
    finally:
        molass.set_cache_dir(None)
    assert len(report.best_shapes) == 3 and "best library shapes" in repr(report)
    assert len(list(tmp_path.glob("kratky-reference-*.npz"))) == 1
    match = decomp.get_kratky_shape_match()
    for (qrg, ky), (qrg2, ky2) in zip(decomp.get_kratky_curves(), match.kratky_curves):
        np.testing.assert_allclose(qrg, qrg2)
        np.testing.assert_allclose(ky, ky2)
    # with the shape match cached, the default report includes the shapes at no cost
    assert decomp.get_continuity_report(rgcurve=rgcurve).best_shapes == report.best_shapes
