import numpy as np
import pytest

import molass
from molass.DataObjects import SecSaxsData
from molass.DataObjects.XrData import XrData
from molass.Testing import Species, simulate_ssd

FRAMES = np.arange(60)


def _ssd(seed=1):
    species = [Species(amp=1.0, center=30, sigma=5, mass=2.0, rg=36.0)]
    return simulate_ssd(species, noise=1.0, seed=seed, xr_frames=FRAMES)


@pytest.fixture
def count_fits(monkeypatch):
    calls = []
    original = XrData.compute_rgcurve

    def counting(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(XrData, "compute_rgcurve", counting)
    return calls


def test_the_rg_curve_is_not_cached_unless_a_cache_dir_is_set(count_fits, tmp_path):
    assert molass.get_cache_dir() is None
    _ssd().get_rg_curve()
    _ssd().get_rg_curve()
    assert len(count_fits) == 2 and list(tmp_path.iterdir()) == []


def test_the_rg_curve_is_loaded_from_the_cache_dir_in_a_later_object(count_fits, tmp_path):
    try:
        molass.set_cache_dir(tmp_path)
        first = _ssd().get_rg_curve()
        assert len(count_fits) == 1
        (path,) = tmp_path.glob("rgcurve-*.npz")

        again = _ssd().get_rg_curve()                   # a new object with the same data: no refit
        assert len(count_fits) == 1
        np.testing.assert_array_equal(again.frames, first.frames)
        np.testing.assert_allclose(again.rgs, first.rgs, equal_nan=True)
        np.testing.assert_allclose(again.scores, first.scores)

        _ssd(seed=2).get_rg_curve()                     # other data: another key, a refit
        assert len(count_fits) == 2 and len(list(tmp_path.glob("rgcurve-*.npz"))) == 2
    finally:
        molass.set_cache_dir(None)


def test_a_corrupt_cache_file_is_ignored_and_rewritten(count_fits, tmp_path):
    try:
        molass.set_cache_dir(tmp_path)
        _ssd().get_rg_curve()
        (path,) = tmp_path.glob("rgcurve-*.npz")
        path.write_bytes(b"garbage")
        _ssd().get_rg_curve()
        assert len(count_fits) == 2                     # refitted, not crashed
        _ssd().get_rg_curve()
        assert len(count_fits) == 2                     # and the file is good again
    finally:
        molass.set_cache_dir(None)


def test_an_unwritable_cache_dir_is_not_an_error(count_fits, tmp_path):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("a file where the directory should be")
    try:
        molass.set_cache_dir(blocker / "cache")
        assert _ssd().get_rg_curve() is not None        # computed; saving silently skipped
    finally:
        molass.set_cache_dir(None)
