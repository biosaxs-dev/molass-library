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
    """coerce_bounds should clip B(q) within the bound envelope."""
    from molass.LowRank.BoundedLrf import estimate_KL, coerce_bounds

    qv, aq, bq, c1_arr, c2_arr, *_ = make_synthetic_rank2()
    c1 = c1_arr[len(c1_arr) // 2]
    Rg = 35
    K, L, R = estimate_KL(qv, aq, bq, Rg, c1)
    aq_corr, bq_coerced, bq_bounds = coerce_bounds(qv, aq, bq, c1, L, R)

    # every coerced value must lie within bounds (allowing tiny float tolerance)
    eps = 1e-12
    assert np.all(bq_coerced >= bq_bounds[0] - eps)
    assert np.all(bq_coerced <= bq_bounds[1] + eps)


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


if __name__ == "__main__":
    test_010_coerce_bounds_clips()
    test_020_conservation()
    test_030_apply_bounded_lrf()
    test_040_rank1_unchanged()
    print("All tests passed.")
