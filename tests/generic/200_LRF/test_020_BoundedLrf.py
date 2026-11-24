"""
    Test Bounded LRF core algorithm with synthetic data.
"""
import pytest
import numpy as np
from molass import get_version
get_version(toml_only=True)


def make_synthetic_rank2(Rg=35, K_true=1.0, num_q=400, num_frames=50, c_max=5.0):
    """Build synthetic M = P @ C with known hard-sphere interparticle term."""
    from molass.SAXS.Theory.SolidSphere import phi

    R = np.sqrt(5 / 3) * Rg
    qv = np.linspace(0.005, 0.5, num_q)
    aq = phi(qv, R) ** 2
    bq = -K_true * phi(qv, 2 * R) * aq

    # concentration profile (Gaussian)
    frames = np.arange(num_frames)
    c1 = c_max * np.exp(-0.5 * ((frames - num_frames / 2) / (num_frames / 8)) ** 2)
    c2 = c1 ** 2
    C_full = np.array([c1, c2])

    P_full = np.column_stack([aq, bq])
    M = P_full @ C_full
    E = np.ones_like(M) * 0.001  # uniform small error

    return qv, aq, bq, c1, c2, C_full, P_full, M, E, R


def test_010_coerce_bounds_clips():
    """coerce_bounds should clip B(q) within the bound envelope for q >= b1 = pi/R."""
    from molass.LowRank.BoundedLrf import estimate_KL, coerce_bounds

    qv, aq, bq, c1_arr, c2_arr, *_ = make_synthetic_rank2()
    c1 = c1_arr[len(c1_arr) // 2]
    Rg = 35
    K, L, R = estimate_KL(qv, aq, bq, Rg, c1)
    aq_corr, bq_coerced, bq_bounds = coerce_bounds(qv, aq, bq, c1, L, R)

    # every coerced value at q >= b1 must lie within bounds (allowing tiny float tolerance)
    eps = 1e-12
    above = qv >= np.pi / R
    assert np.all(bq_coerced[above] >= bq_bounds[0][above] - eps)
    assert np.all(bq_coerced[above] <= bq_bounds[1][above] + eps)


def test_015_no_clipping_below_b1():
    """molass-library#411: points below b1 = pi/R keep B(q) and A(q) of the plain rank-2 solution,
    even when the envelope would cut real B(q) there (short-range B(q), forced L = 2)."""
    from molass.SAXS.Theory.SolidSphere import phi
    from molass.LowRank.BoundedLrf import estimate_KL, coerce_bounds

    Rg = 33.0
    R = np.sqrt(5 / 3) * Rg
    qv = np.linspace(0.0075, 0.4, 740)
    aq = phi(qv, R) ** 2
    bq = -0.51 * phi(qv, 2 * R * 0.6) * aq        # exactly rank 2, structure at higher q than a hard sphere
    c1 = 1.0
    K, L, R_ = estimate_KL(qv, aq, bq, Rg, c1)

    # the envelope alone would clip real low-q B(q) here (this is the failure of #411)
    low = qv < 0.03
    assert np.mean(np.abs(bq[low]) > (1 / (qv * L * R_) ** 2 * aq / c1)[low]) > 0.3

    aq_corr, bq_coerced, _ = coerce_bounds(qv, aq, bq, c1, L, R_)
    below = qv < np.pi / R_
    np.testing.assert_array_equal(bq_coerced[below], bq[below])
    np.testing.assert_array_equal(aq_corr[below], aq[below])
    # the low-q A(q) is exact, not corrupted by redistribution (it was off by 14 % before)
    assert np.max(np.abs((aq_corr - aq) / aq)[low]) < 1e-12


def test_020_conservation():
    """A'*c1 + B'*c2 == A*c1 + B*c2  (row-wise intensity sum preserved)."""
    from molass.LowRank.BoundedLrf import estimate_KL, coerce_bounds

    qv, aq, bq, c1_arr, c2_arr, *_ = make_synthetic_rank2()
    c1 = c1_arr[len(c1_arr) // 2]
    c2 = c1 ** 2
    Rg = 35
    K, L, R = estimate_KL(qv, aq, bq, Rg, c1)
    aq_corr, bq_coerced, _ = coerce_bounds(qv, aq, bq, c1, L, R)

    original_sum = aq * c1 + bq * c2
    corrected_sum = aq_corr * c1 + bq_coerced * c2
    np.testing.assert_allclose(corrected_sum, original_sum, atol=1e-10)


def test_030_apply_bounded_lrf():
    """apply_bounded_lrf should return corrected P with rank-2 bounded."""
    from molass.LowRank.BoundedLrf import apply_bounded_lrf

    qv, aq, bq, c1_arr, c2_arr, C_full, P_full, M, E, R = make_synthetic_rank2()

    # Mock guinier_objects with an object that has .Rg
    class MockGuinier:
        def __init__(self, Rg):
            self.Rg = Rg

    guinier_objects = [MockGuinier(35)]
    ranks = [2]

    P_trunc, info = apply_bounded_lrf(qv, P_full, C_full, ranks, guinier_objects)

    # P_trunc should have shape (num_q, 1) — one component
    assert P_trunc.shape == (len(qv), 1)
    # info should contain entry for component 0
    assert 0 in info
    assert 'K' in info[0]
    assert 'bq_coerced' in info[0]


def test_040_rank1_unchanged():
    """apply_bounded_lrf should not modify rank-1 components."""
    from molass.LowRank.BoundedLrf import apply_bounded_lrf
    from molass.SAXS.Theory.SolidSphere import phi

    Rg = 30
    R = np.sqrt(5 / 3) * Rg
    qv = np.linspace(0.005, 0.5, 200)
    aq = phi(qv, R) ** 2
    c1 = 5.0 * np.exp(-0.5 * ((np.arange(40) - 20) / 5) ** 2)
    C_full = np.array([c1])
    P_full = aq.reshape(-1, 1)

    class MockGuinier:
        def __init__(self, Rg):
            self.Rg = Rg

    guinier_objects = [MockGuinier(Rg)]
    ranks = [1]

    P_trunc, info = apply_bounded_lrf(qv, P_full, C_full, ranks, guinier_objects)
    np.testing.assert_array_equal(P_trunc, P_full)
    assert len(info) == 0


def test_050_bounded_lrf_info_repr_is_concise():
    """BoundedLrfInfo's repr must summarize (not dump the full bq_* arrays) --
    dict-style field access must still work unchanged (molass-library#276
    follow-up)."""
    from molass.LowRank.BoundedLrf import apply_bounded_lrf

    qv, aq, bq, c1_arr, c2_arr, C_full, P_full, M, E, R = make_synthetic_rank2()

    class MockGuinier:
        def __init__(self, Rg):
            self.Rg = Rg

    guinier_objects = [MockGuinier(35)]
    ranks = [2]

    _, info = apply_bounded_lrf(qv, P_full, C_full, ranks, guinier_objects)
    entry = info[0]

    # dict-style access still works exactly as before
    assert isinstance(entry['K'], float)
    assert isinstance(entry['bq_coerced'], np.ndarray)

    r = repr(entry)
    assert r.startswith("BoundedLrfInfo(")
    assert "K=" in r and "L=" in r and "R=" in r and "Rg=" in r
    # the raw array values must NOT appear in the repr (only their shape)
    assert "bq_coerced=<array" in r
    assert str(entry['bq_coerced'][0]) not in r


if __name__ == "__main__":
    test_010_coerce_bounds_clips()
    test_015_no_clipping_below_b1()
    test_020_conservation()
    test_030_apply_bounded_lrf()
    test_040_rank1_unchanged()
    test_050_bounded_lrf_info_repr_is_concise()
    print("All tests passed.")
