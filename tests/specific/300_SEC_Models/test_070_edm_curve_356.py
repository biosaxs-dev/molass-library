"""The documented public EDM function (molass-library#356): the facts its docstring states, checked numerically."""
import inspect

import numpy as np
import pytest

from molass.SEC.Models.EdmFunction import edm_curve
from molass_legacy.SecTheory.Edm import edm_func
from molass_legacy.Models.RateTheory.EDM import edm_impl

T = np.linspace(0.01, 600, 12001)
BASE = dict(u=0.5, a=1.0, e=0.4, Dz=0.05)
trapezoid = getattr(np, "trapezoid", None) or np.trapz        # numpy < 2.0 has only trapz


def _skew(y, t=T):
    w = y / trapezoid(y, t)
    m = trapezoid(w * t, t)
    s = np.sqrt(trapezoid(w * (t - m) ** 2, t))
    return trapezoid(w * (t - m) ** 3, t) / s ** 3


def test_it_is_the_function_molass_uses():
    y = edm_curve(T, t0=3.0, b=0.7, c_inj=1.5, **BASE)
    assert np.array_equal(y, edm_impl(T, 3.0, 0.5, 1.0, 0.7, 0.4, 0.05, 1.5))      # edm_impl's parameter order
    assert np.array_equal(y, edm_func(T - 3.0, 0.5, 1.0, 0.7, 0.4, 0.05, 1.5))
    assert np.array_equal(edm_curve(T, b=0.7, c_inj=1.5, **BASE), edm_func(T, 0.5, 1.0, 0.7, 0.4, 0.05, 1.5))


def test_arguments_are_keywords():
    sig = inspect.signature(edm_curve)
    assert [p.name for p in sig.parameters.values() if p.kind is p.KEYWORD_ONLY] == ["t0", "u", "a", "b", "e", "Dz", "c_inj"]
    with pytest.raises(TypeError):
        edm_curve(T, 0.5, 1.0, 1.0, 0.4, 0.05, 1.5)


def test_sign_of_b_decides_tailing_or_fronting():
    skew = {b: _skew(edm_curve(T, b=b, c_inj=1.5, **BASE)) for b in (-3, -1, 0, 1, 3)}
    assert skew[-3] < skew[-1] < -0.2                              # fronting
    assert 0.1 < skew[0] < 0.4                                     # linear isotherm: axial dispersion only
    assert 0.5 < skew[1] < skew[3]                                 # tailing
    assert skew[1] == pytest.approx(0.73, abs=0.01) and skew[3] == pytest.approx(0.93, abs=0.01)


def test_b_zero_is_the_continuous_limit():
    y0 = edm_curve(T, b=0.0, c_inj=1.0, **BASE)
    for b in (1e-3, 1e-5):
        assert np.max(np.abs(edm_curve(T, b=b, c_inj=1.0, **BASE) - y0)) < 1e-3 * y0.max()


def test_shape_depends_on_b_and_c_inj_through_their_product():
    def normalized(b, c):
        y = edm_curve(T, b=b, c_inj=c, **BASE)
        return y / trapezoid(y, T), y.max()
    ref, ref_max = normalized(1.0, 2.0)
    for b, c in [(2.0, 1.0), (0.5, 4.0), (4.0, 0.5)]:
        y, ymax = normalized(b, c)
        assert np.max(np.abs(y - ref)) < 2e-3 * ref.max()
        assert ymax / ref_max == pytest.approx(1.0 / b, rel=0.01)      # height ~ 1/b at fixed b*c_inj
    other, _ = normalized(1.0, 1.0)                                    # a different product: a different shape
    assert np.max(np.abs(other - ref)) > 0.1 * ref.max()


def test_a_is_not_interchangeable_with_b():
    def normalized(a, b):
        y = edm_curve(T, u=0.5, a=a, b=b, e=0.4, Dz=0.05, c_inj=2.0)
        return y / trapezoid(y, T)
    ref = normalized(1.0, 1.0)
    for a, b in [(2.0, 0.5), (0.5, 2.0)]:                              # same a*b
        assert np.max(np.abs(normalized(a, b) - ref)) > 0.5 * ref.max()
