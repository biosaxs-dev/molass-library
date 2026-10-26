"""
Test molass.Homogeneity: concentration proxies, ratio curves, flatness statistics (molass-library#322, #323).
"""
import numpy as np
import pytest
from types import SimpleNamespace
from molass.Homogeneity import (ConcentrationProxy, ProxyRatio, independent_axes,
                                xr_q_proxy, uv_proxy, xr_i0_proxy, band_average)


FRAMES = np.arange(60)


def _proxy(name, values, source="xr"):
    return ConcentrationProxy(name, FRAMES, values, source, uses_mapping=(source == "uv"))


def _conc():
    return np.exp(-0.5 * ((FRAMES - 30) / 10.0) ** 2) + 0.05


def test_010_constant_ratio_is_flat_within_noise():
    rng = np.random.default_rng(1)
    conc = _conc()
    r = ProxyRatio(_proxy("I(0)", 3.0 * conc * (1 + 0.01 * rng.standard_normal(60))), _proxy("A280", conc, "uv"))
    f = r.flatness((10, 50))
    assert f.n == 41
    assert f.median == pytest.approx(3.0, rel=0.01)
    assert f.sd_over_noise < 2
    assert abs(f.tilt_z) < 4


def test_020_tilted_ratio_is_detected():
    conc = _conc()
    r = ProxyRatio(_proxy("I(0)", conc * (1 + 0.3 * (FRAMES - 30) / 60)), _proxy("A280", conc, "uv"))
    f = r.flatness((10, 50))
    assert f.tilt == pytest.approx(0.3 * 40 / 60, rel=0.1)
    assert f.tilt_z > 10
    assert f.sd_over_noise > 10


def test_030_deviation_and_scale():
    conc = _conc()
    r = ProxyRatio(_proxy("A320", 0.01 * conc), _proxy("A280", conc))
    dev = r.deviation((10, 50), scale=1.0)           # ratio near 0: absolute deviation
    assert np.nanmax(np.abs(dev[10:51])) < 1e-12
    with pytest.raises(ValueError):
        ProxyRatio(_proxy("a", 0 * conc), _proxy("b", conc)).flatness((10, 50))


def test_040_nonpositive_denominator_gives_nan():
    den = _conc()
    den[5] = 0.0
    den[6] = -1.0
    r = ProxyRatio(_proxy("a", _conc()), _proxy("b", den))
    assert np.isnan(r.values[5]) and np.isnan(r.values[6]) and np.isfinite(r.values[7])


def test_050_depends_on_mapping():
    xr_a, xr_b, uv_a = _proxy("I(0)", _conc()), _proxy("I(0.02)", _conc()), _proxy("A280", _conc(), "uv")
    assert not ProxyRatio(xr_a, xr_b).depends_on_mapping
    assert ProxyRatio(xr_a, uv_a).depends_on_mapping


def test_060_independent_axes():
    # the three ratios among I(0), I(0.02), A280 are one dependent triple: 2 axes
    assert independent_axes([("I(0)", "I(0.02)"), ("I(0)", "A280"), ("A280", "I(0.02)")]) == 2
    # a chain over four proxies: 3 axes; two separate pairs: 2 axes
    assert independent_axes([("a", "b"), ("b", "c"), ("c", "d")]) == 3
    assert independent_axes([("a", "b"), ("c", "d")]) == 2
    assert independent_axes([]) == 0
    p, q = _proxy("I(0)", _conc()), _proxy("A280", _conc(), "uv")
    assert independent_axes([ProxyRatio(p, q)]) == 1


def test_070_band_average_and_errors():
    M = np.arange(12.0).reshape(4, 3)
    np.testing.assert_allclose(band_average(M, [1, 2, 3, 4], 2.5, 0.6), M[1:3].mean(axis=0))
    with pytest.raises(ValueError):
        band_average(M, [1, 2, 3, 4], 10, 0.5)


def test_080_xr_and_uv_proxies_on_fake_data():
    xr = SimpleNamespace(M=np.tile(np.arange(1, 11.0)[:, None], (1, 5)), qv=np.linspace(0.01, 0.10, 10),
                         jv=np.arange(5))
    p = xr_q_proxy(xr, 0.04, half_width=0.004)
    assert p.name == "I(0.04)" and p.source == "xr" and not p.uses_mapping
    np.testing.assert_allclose(p.values, 4.0)

    uv = SimpleNamespace(M=np.tile(np.arange(10.0), (3, 1)), wv=np.array([260.0, 280.0, 290.0]),
                         jv=np.arange(10))
    mapping = SimpleNamespace(xr_to_uv=lambda x: 2.0 * np.asarray(x) + 1.0)
    frames = np.arange(6)
    a = uv_proxy(uv, 280, mapping, frames, half_width=1)
    assert a.name == "A280" and a.uses_mapping
    np.testing.assert_allclose(a.values[:5], [1.0, 3.0, 5.0, 7.0, 9.0])
    assert np.isnan(a.values[5])                       # UV frame 11 is outside the UV range
    shifted = uv_proxy(uv, 280, mapping, frames, delta=1.0, half_width=1)
    np.testing.assert_allclose(shifted.values[1:5], [1.0, 3.0, 5.0, 7.0])     # delta = +1 frame: later


def test_090_xr_i0_proxy_uses_rgcurve_i0s():
    rg = SimpleNamespace(frames=np.arange(3), i0s=np.array([1.0, np.nan, 3.0]))
    p = xr_i0_proxy(rg)
    assert p.name == "I(0)" and p.source == "xr"
    np.testing.assert_allclose(p.values, [1.0, np.nan, 3.0])


@pytest.fixture(scope="module")
def sample1():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    return SSD(SAMPLE1).trimmed_copy().corrected_copy()


def test_100_sample1_proxies_and_ratios(sample1):
    ssd = sample1
    mapping = ssd.get_mapping()
    frames = ssd.xr.jv
    i1 = xr_q_proxy(ssd.xr, 0.02)
    a280, a290 = (uv_proxy(ssd.uv, w, mapping, frames) for w in (280, 290))
    assert len(i1.values) == len(a280.values) == len(frames)
    ratio = ProxyRatio(a280, a290)
    assert not ratio.depends_on_mapping
    f = ratio.flatness((145, 170))          # peak 2 core of SAMPLE1: UV spectrum constant to < 1 %
    assert f.sd < 0.02
    assert ProxyRatio(i1, a280).depends_on_mapping
