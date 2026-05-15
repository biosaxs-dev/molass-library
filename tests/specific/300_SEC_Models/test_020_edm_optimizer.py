"""
Test optimize_edm_xr_decomposition: e_bounds=(0,1) constraint.

See:
  https://github.com/biosaxs-dev/molass-library/issues/176 (e_bounds)
"""
import numpy as np
import pytest
from molass_legacy.Models.RateTheory.EDM import edm_impl
from molass.SEC.Models.EdmOptimizer import optimize_edm_xr_decomposition


# ---------------------------------------------------------------------------
# Minimal fakes
# ---------------------------------------------------------------------------

class _FakeCurve:
    """Component curve with x, y, and a peak at peak_frame."""
    def __init__(self, x, peak_frame, amplitude=1.0, width=10.0):
        self.x = np.asarray(x, dtype=float)
        self.y = amplitude * np.exp(-0.5 * ((self.x - peak_frame) / width) ** 2)

    def get_xy(self):
        return self.x, self.y


class _FakeIcurve:
    def __init__(self, x, y):
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)

    def get_xy(self):
        return self.x, self.y


class _FakeDecomposition:
    def __init__(self, x, ccurves):
        total_y = sum(c.y for c in ccurves)
        self.xr_icurve = _FakeIcurve(x, total_y)
        self.xr_ccurves = ccurves
        self.num_components = len(ccurves)


def _make_edm_params(t0=100.0, u=1.0, a=1.0, b=0.5, e=0.5, Dz=0.01, cinj=1.0):
    """Return a single-component EDM parameter vector."""
    return np.array([t0, u, a, b, e, Dz, cinj])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_e_bounded_between_0_and_1():
    """After optimization with e_bounds=(0,1) (default), e must stay in [0,1]."""
    x = np.linspace(50, 200, 300)

    # Component 0: large dominant component
    p0 = _make_edm_params(t0=80.0,  u=1.0, a=1.0, b=0.5, e=0.5, Dz=0.01, cinj=1.0)
    # Component 1: small minority component — prone to e > 1 without bounds
    p1 = _make_edm_params(t0=120.0, u=1.0, a=0.1, b=0.5, e=0.3, Dz=0.01, cinj=0.1)

    y0 = edm_impl(x, *p0)
    y1 = edm_impl(x, *p1)

    ccurve0 = _FakeCurve(x, x[np.argmax(y0)])
    ccurve1 = _FakeCurve(x, x[np.argmax(y1)], amplitude=0.1)
    decomp = _FakeDecomposition(x, [ccurve0, ccurve1])

    # Slightly perturb init to encourage the optimizer to wander
    init = np.array([p0, p1]) * np.array([
        [1.0, 1.0, 1.0, 1.0, 1.5, 1.0, 1.0],  # e perturbed above 1
        [1.0, 1.0, 1.0, 1.0, 0.8, 1.0, 1.0],
    ])

    ccurves_opt = optimize_edm_xr_decomposition(decomp, init)
    for i, ccurve in enumerate(ccurves_opt):
        e_val = ccurve.params[4]
        assert 0.0 <= e_val <= 1.0, (
            f"Component {i}: e={e_val:.4f} outside [0,1] — bounds not applied"
        )


def test_e_bounds_none_disables_constraint():
    """With e_bounds=None the optimizer is free — e may wander outside [0,1]."""
    x = np.linspace(50, 200, 300)
    p0 = _make_edm_params(t0=100.0, u=1.0, a=0.05, b=0.5, e=0.5, Dz=0.01, cinj=0.1)
    ccurve0 = _FakeCurve(x, 100.0, amplitude=0.05)
    decomp = _FakeDecomposition(x, [ccurve0])

    # Init with e well above 1 and tiny amplitude — without bounds the optimizer
    # can stay above 1 if that minimises the residual
    init = np.array([_make_edm_params(t0=100.0, u=1.0, a=0.05, b=0.5, e=1.5, Dz=0.01, cinj=0.1)])
    # Just check it runs without error; we do not assert on the e value
    ccurves_opt = optimize_edm_xr_decomposition(decomp, init, e_bounds=None)
    assert len(ccurves_opt) == 1


def test_shared_column_returns_correct_number_of_curves():
    """shared_column=True must return one EdmComponentCurve per component,
    with shared t0/u/e/Dz, per-component a/b/cinj, and physical bounds met."""

    x = np.linspace(50, 200, 300)

    # Two synthetic EDM components with known peak positions and different amplitudes
    # (different cinj breaks the swap-symmetry so the optimizer converges reliably).
    # Use the actual EDM signal as the target data so the optimizer has a clear minimum.
    # Component 0 (larger molecule, earlier elution): a=0.8, cinj=2.0
    # Component 1 (smaller molecule, later elution):  a=2.0, cinj=0.5
    p0 = _make_edm_params(t0=70.0, u=1.2, a=0.8, b=0.5, e=0.45, Dz=0.01, cinj=2.0)
    p1 = _make_edm_params(t0=70.0, u=1.2, a=2.0, b=0.5, e=0.45, Dz=0.01, cinj=0.5)

    y0 = edm_impl(x, *p0)
    y1 = edm_impl(x, *p1)

    peak_frame_0 = float(x[np.argmax(y0)])
    peak_frame_1 = float(x[np.argmax(y1)])

    # Use Gaussian position-anchors at the EDM peak locations
    ccurve0 = _FakeCurve(x, peak_frame_0, amplitude=2.0)
    ccurve1 = _FakeCurve(x, peak_frame_1, amplitude=0.5)

    # Use actual EDM sum as target data (not Gaussian sum) — gives the optimizer
    # a clear minimum near the true parameters.
    class _EDMDecomposition:
        def __init__(self, x, y, ccurves):
            self.xr_icurve = _FakeIcurve(x, y)
            self.xr_ccurves = ccurves
            self.num_components = len(ccurves)

    decomp = _EDMDecomposition(x, y0 + y1, [ccurve0, ccurve1])
    init = np.array([p0, p1])

    ccurves_opt = optimize_edm_xr_decomposition(decomp, init, shared_column=True)

    # Correct number of components returned
    assert len(ccurves_opt) == 2

    # All components share t0, u, e, Dz (identical float values)
    t0_vals = [c.params[0] for c in ccurves_opt]
    u_vals  = [c.params[1] for c in ccurves_opt]
    e_vals  = [c.params[4] for c in ccurves_opt]
    Dz_vals = [c.params[5] for c in ccurves_opt]
    assert t0_vals[0] == pytest.approx(t0_vals[1], rel=1e-9), "t0 must be shared"
    assert u_vals[0]  == pytest.approx(u_vals[1],  rel=1e-9), "u must be shared"
    assert e_vals[0]  == pytest.approx(e_vals[1],  rel=1e-9), "e must be shared"
    assert Dz_vals[0] == pytest.approx(Dz_vals[1], rel=1e-9), "Dz must be shared"

    # e stays in physical range (0.2, 0.85)
    for i, c in enumerate(ccurves_opt):
        e_val = c.params[4]
        assert 0.2 <= e_val <= 0.85, f"Component {i}: e={e_val:.4f} outside (0.2, 0.85)"

    # cinj stays at or above cinj_min=0.05
    for i, c in enumerate(ccurves_opt):
        cinj_val = c.params[6]
        assert cinj_val >= 0.05, f"Component {i}: cinj={cinj_val:.4f} below cinj_min"

    # K_SEC order preserved: component 0 (anchored near peak_frame_0 < peak_frame_1)
    # must have smaller a than component 1.  This is the key correctness criterion:
    # larger a → more retained → later elution.
    a0, a1 = ccurves_opt[0].params[2], ccurves_opt[1].params[2]
    assert a0 < a1, (
        f"K_SEC order wrong: a[0]={a0:.4f} >= a[1]={a1:.4f}, "
        f"but comp 0 peaks at {peak_frame_0:.1f} < comp 1 at {peak_frame_1:.1f}"
    )
