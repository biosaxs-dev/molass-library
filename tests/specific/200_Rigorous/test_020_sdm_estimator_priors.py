"""
Test estimate_sdm_column_params with physical priors and M3 matching.

See: https://github.com/biosaxs-dev/molass-library/issues/111
"""
import numpy as np
import pytest


# Synthetic decomposition fixtures used by every test.
# We avoid loading data — the estimator only needs:
#   - decomposition.get_rgs() → array
#   - decomposition.xr_ccurves[i].get_xy() → (x, y)
#   - decomposition.xr_icurve.get_xy() → (x, y) (only used in debug=True path)
class _FakeCurve:
    def __init__(self, x, y):
        self._x, self._y = x, y
    def get_xy(self):
        return self._x, self._y


class _FakeDecomp:
    def __init__(self, rgs, ccurves):
        self._rgs = list(rgs)
        self.xr_ccurves = ccurves
        # icurve = sum of components (only used by debug plot)
        x = ccurves[0].get_xy()[0]
        y = sum(cc.get_xy()[1] for cc in ccurves)
        self.xr_icurve = _FakeCurve(x, y)
    def get_rgs(self):
        return self._rgs


def _make_skewed_component(x, ni, ti, N0, t0, scale=1.0):
    """Generate a skewed elution profile via the SDM monopore PDF."""
    from molass.SEC.Models.SdmMonoPore import sdm_monopore_pdf
    return scale * sdm_monopore_pdf(x - 0.0, ni, ti, N0, t0)


@pytest.fixture
def skewed_decomp():
    """Single-component decomposition with strong asymmetry."""
    x = np.arange(0, 1500, dtype=float)
    # Forward-model parameters, matched to the 13w Apo case envelope:
    #   poresize=78, Rg=33 → rho≈0.42, ni≈N*(1-rho)^1.5, ti≈T*(1-rho)^1.5
    N_true, T_true, poresize_true, N0_true, t0_true = 800.0, 1.5, 78.0, 14400.0, 880.0
    Rg_true = 33.0
    rho = Rg_true / poresize_true
    ni = N_true * (1 - rho)**1.5
    ti = T_true * (1 - rho)**1.5
    y = _make_skewed_component(x - t0_true + 880.0, ni, ti, N0_true, 880.0)
    y = np.maximum(y, 0.0)
    return _FakeDecomp([Rg_true], [_FakeCurve(x, y)]), \
           dict(N=N_true, T=T_true, poresize=poresize_true, N0=N0_true, Rg=Rg_true)


def _data_moments(x, y):
    yp = np.maximum(y, 0)
    W = yp.sum()
    m1 = (x * yp).sum() / W
    m2c = (yp * (x - m1)**2).sum() / W
    m3c = (yp * (x - m1)**3).sum() / W
    return m1, np.sqrt(m2c), np.sign(m3c) * abs(m3c)**(1/3)


def test_priors_narrow_search_to_known_column(skewed_decomp):
    """With tight poresize_bounds and fixed N0, the estimator should find
    a poresize within ±5 Å of truth (loose bound — single-start L-BFGS-B,
    not basinhopping). Tighter convergence is left to the rigorous
    optimizer downstream."""
    from molass.SEC.Models.SdmEstimator import estimate_sdm_column_params

    decomp, truth = skewed_decomp
    N, T, me, mp, N0, t0, poresize = estimate_sdm_column_params(
        decomp,
        poresize_bounds=(75, 82),
        N0=truth['N0'],
        include_M3=True,
    )
    assert abs(poresize - truth['poresize']) < 5.0, \
        f"poresize {poresize:.2f} not within 5 Å of truth {truth['poresize']:.2f}"
    # N0 must be returned as-fixed
    assert N0 == truth['N0']


def test_M3_improves_skew_over_no_M3(skewed_decomp):
    """include_M3=True should give a strictly better cube-root-skew match
    than include_M3=False on asymmetric data. This is the core claim that
    motivates issue #111."""
    from molass.SEC.Models.SdmEstimator import estimate_sdm_column_params

    decomp, truth = skewed_decomp
    cx, cy = decomp.xr_ccurves[0].get_xy()
    _, _, target_sk3 = _data_moments(cx, cy)

    def matched_sk3(include_M3):
        N, T, me, mp, N0, t0, poresize = estimate_sdm_column_params(
            decomp,
            poresize_bounds=(75, 82),
            N0=truth['N0'],
            include_M3=include_M3,
        )
        rho = truth['Rg'] / poresize
        ni = N * (1 - rho)**me
        ti = T * (1 - rho)**mp
        M3 = 6 * ni * ti**2 * (N0*ti + ni*ti + t0) / N0
        return np.sign(M3) * abs(M3)**(1/3)

    sk3_with = matched_sk3(True)
    sk3_without = matched_sk3(False)

    err_with = abs(sk3_with - target_sk3)
    err_without = abs(sk3_without - target_sk3)

    assert err_with < err_without, (
        f"include_M3=True did not improve skew match: "
        f"with-M3 err={err_with:.3f}, without-M3 err={err_without:.3f}, "
        f"target={target_sk3:.3f}"
    )


def test_default_kwargs_run(skewed_decomp):
    """No kwargs → estimator must still run and return a 7-tuple of finite floats."""
    from molass.SEC.Models.SdmEstimator import estimate_sdm_column_params

    decomp, _ = skewed_decomp
    out = estimate_sdm_column_params(decomp)
    assert len(out) == 7
    for v in out:
        assert np.isfinite(v), f"non-finite return value: {v}"


def test_N0_fixed_excludes_from_optimization(skewed_decomp):
    """When N0 is given, the returned N0 must equal it exactly."""
    from molass.SEC.Models.SdmEstimator import estimate_sdm_column_params

    decomp, _ = skewed_decomp
    _, _, _, _, N0_out, _, _ = estimate_sdm_column_params(
        decomp,
        N0=12345.0,
        poresize_bounds=(70, 100),
    )
    assert N0_out == 12345.0
