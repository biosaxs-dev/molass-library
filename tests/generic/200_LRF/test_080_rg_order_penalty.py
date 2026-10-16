"""Tests for the Rg-order penalty of the quick proportional decomposition (molass-library#295)."""
import warnings
import numpy as np
import pytest
from molass.Decompose.RgOrder import RgOrderPenalty, estimate_reference_rg


def make_two_component_data(rg_first, rg_second, num_q=120, num_frames=300):
    qv = np.linspace(0.006, 0.3, num_q)
    P = np.column_stack([np.exp(-(qv * rg) ** 2 / 3) for rg in (rg_first, rg_second)])
    frames = np.arange(num_frames, dtype=float)
    C = np.array([np.exp(-0.5 * ((frames - mu) / 12) ** 2) * h for mu, h in ((120, 1.0), (170, 0.6))])
    return qv, P @ C, C


def test_estimate_reference_rg_recovers_guinier_profile():
    qv = np.linspace(0.006, 0.3, 120)
    rg = estimate_reference_rg(qv, np.exp(-(qv * 45.0) ** 2 / 3))
    assert rg == pytest.approx(45.0, rel=0.05)


def test_estimate_reference_rg_none_for_non_decaying_profile():
    qv = np.linspace(0.006, 0.3, 50)
    assert estimate_reference_rg(qv, np.ones_like(qv)) is None


def test_violation_zero_for_sec_ordered_and_positive_for_swapped():
    qv, M, C = make_two_component_data(rg_first=60.0, rg_second=30.0)
    pen = RgOrderPenalty(M, qv, 2)
    assert pen.enabled
    assert pen.violation(list(C)) == 0.0
    assert pen.term(list(C)) == 0.0

    qv, M_sw, C = make_two_component_data(rg_first=30.0, rg_second=60.0)
    pen_sw = RgOrderPenalty(M_sw, qv, 2)
    assert pen_sw.enabled
    assert pen_sw.violation(list(C)) > 0.0
    assert pen_sw.term(list(C)) > 0.0


def test_proxy_orders_components_like_true_rgs():
    qv, M, C = make_two_component_data(rg_first=60.0, rg_second=30.0)
    rg = RgOrderPenalty(M, qv, 2).rg_proxy(list(C))
    assert rg[0] > rg[1]


@pytest.mark.parametrize("weight, num_components", [(0, 2), (0.1, 1)])
def test_disabled_cases(weight, num_components):
    qv, M, C = make_two_component_data(60.0, 30.0)
    pen = RgOrderPenalty(M, qv, num_components, weight=weight)
    assert not pen.enabled
    assert pen.term(list(C)) == 0.0


def test_quick_decomposition_accepts_rg_order_weight():
    from molass_data import SAMPLE3
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE3)
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)   # unknown kwargs would warn
        d_default = ssd.quick_decomposition(proportions=[3, 2, 1])
        d_off = ssd.quick_decomposition(proportions=[3, 2, 1], rg_order_weight=0)
    assert d_default.num_components == d_off.num_components == 3
    assert np.all(np.isfinite(d_default.get_rgs()))
    assert np.all(np.isfinite(d_off.get_rgs()))
