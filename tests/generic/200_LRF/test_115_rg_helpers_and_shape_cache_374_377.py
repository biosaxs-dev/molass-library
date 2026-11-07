import types

import numpy as np
import pytest

from molass.Continuity.Indicators import rg_point_noise, rg_drop
from molass.Guinier.RgCurve import RgCurve
from molass.Kratky import ShapeMatch
from molass.Kratky.ShapeMatch import kratky_curves_of


def _curve(n=40, noise=0.4, seed=0):
    rng = np.random.default_rng(seed)
    frames = np.arange(n)
    return RgCurve(frames, 40.0 - 0.5*frames + noise*rng.standard_normal(n), np.full(n, 0.9))


def test_rgcurve_noise_and_drop_use_the_reliable_frames():
    curve = _curve()
    frames, rgs = curve.reliable()
    assert curve.noise() == pytest.approx(rg_point_noise(frames, rgs))
    assert curve.drop() == pytest.approx(rg_drop(rgs))
    assert curve.drop() == pytest.approx(0.5*35, rel=0.15)          # the ramp falls 0.5 A per frame
    # unreliable frames (low score) are left out, as in reliable()
    scores = np.full(40, 0.9); scores[::2] = 0.2
    sparse = RgCurve(np.arange(40), curve.rgs, scores)
    assert len(sparse.reliable()[0]) == 20 and np.isnan(sparse.noise())      # no two consecutive frames left


def test_rgcurve_noise_and_drop_are_nan_without_reliable_frames():
    curve = RgCurve([1, 2, 3], [np.nan, 50.0, 100.0], [0.9, 0.2, 0.9])
    assert np.isnan(curve.noise()) and np.isnan(curve.drop())


def test_kratky_curves_of_matches_the_definition_and_marks_missing_rg():
    q = np.linspace(0.01, 0.3, 50)
    P = np.vstack([np.exp(-q**2*30**2/3), np.exp(-q**2*20**2/3)]).T*5.0
    curves = kratky_curves_of(q, P, [30.0, np.nan], [5.0, 5.0])
    qrg, ky = curves[0]
    np.testing.assert_allclose(qrg, q*30.0)
    np.testing.assert_allclose(ky, (q*30.0)**2*P[:, 0]/5.0)
    assert curves[1] is None
    assert kratky_curves_of(q, P, [None, 20.0], [5.0, 5.0])[0] is None
    with pytest.raises(ValueError):
        kratky_curves_of(q, P[:10], [30.0, 20.0], [5.0, 5.0])


def _fake_library():
    sphere = lambda x: np.exp(-x**2/3)
    return [types.SimpleNamespace(name="fake-a", Rg=30.0, P_fn=sphere),
            types.SimpleNamespace(name="fake-b", Rg=45.0, P_fn=lambda x: np.exp(-x**2/5))]


def test_reference_curves_are_built_once_then_read_from_the_disk_cache(tmp_path):
    from molass.Global import Cache
    notices = []
    shapes = _fake_library()
    try:
        Cache.set_cache_dir(tmp_path)
        ShapeMatch._PRIMED_REFERENCE_CURVES.clear()
        ShapeMatch._prime_reference_curves(shapes, 3.0, notify=notices.append)
        assert len(notices) == 1 and "first use" in notices[0] and str(tmp_path) in notices[0]
        files = list(tmp_path.glob("kratky-reference-*.npz"))
        assert len(files) == 1
        built = {k: v for k, v in ShapeMatch._PRIMED_REFERENCE_CURVES.items()}

        ShapeMatch._PRIMED_REFERENCE_CURVES.clear()                 # a new process: nothing in memory
        ShapeMatch._prime_reference_curves(shapes, 3.0, notify=notices.append)
        assert len(notices) == 1                                    # no second notice: read from the disk
        for key, (grid, curve) in built.items():
            np.testing.assert_array_equal(ShapeMatch._PRIMED_REFERENCE_CURVES[key][1], curve)

        shapes[0].Rg = 31.0                                         # another library: another file
        ShapeMatch._prime_reference_curves(shapes, 3.0, notify=notices.append)
        assert len(notices) == 2 and len(list(tmp_path.glob("kratky-reference-*.npz"))) == 2
    finally:
        Cache.set_cache_dir(None)
        ShapeMatch._PRIMED_REFERENCE_CURVES.clear()


def test_an_unreadable_cache_file_is_rebuilt(tmp_path):
    from molass.Global import Cache
    notices = []
    shapes = _fake_library()
    try:
        Cache.set_cache_dir(tmp_path)
        ShapeMatch._PRIMED_REFERENCE_CURVES.clear()
        ShapeMatch._prime_reference_curves(shapes, 3.0, notify=notices.append)
        (path,) = tmp_path.glob("kratky-reference-*.npz")
        path.write_bytes(b"not an npz file")
        ShapeMatch._PRIMED_REFERENCE_CURVES.clear()
        ShapeMatch._prime_reference_curves(shapes, 3.0, notify=notices.append)
        assert len(notices) == 2                                    # rebuilt, no crash
        ShapeMatch._PRIMED_REFERENCE_CURVES.clear()
        ShapeMatch._prime_reference_curves(shapes, 3.0, notify=notices.append)
        assert len(notices) == 2                                    # and the file is good again
    finally:
        Cache.set_cache_dir(None)
        ShapeMatch._PRIMED_REFERENCE_CURVES.clear()
