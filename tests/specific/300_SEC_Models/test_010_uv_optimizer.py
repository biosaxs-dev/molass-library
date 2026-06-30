"""
Test optimize_uv_decomposition: physics-based initial scale and debug output.

See:
  https://github.com/biosaxs-dev/molass-library/issues/171 (debug output)
  https://github.com/biosaxs-dev/molass-library/issues/172 (physics-based initial scale)
"""
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Minimal fakes — no data loading required
# ---------------------------------------------------------------------------

class _FakeMapping:
    """Mapping: XR frame → UV frame via slope*xr + intercept.
    Matches the interface expected by optimize_uv_decomposition."""
    def __init__(self, slope, intercept):
        self.slope = slope
        self.intercept = intercept
        # Also expose .a/.b for molass-library Mapping compatibility
        self.a = slope
        self.b = intercept

    def __call__(self, xr):
        return self.slope * xr + self.intercept

    def inv(self, uv):
        return (uv - self.intercept) / self.slope


class _FakeXrCurve:
    """Minimal XR component curve.  get_y(xq) interpolates a Gaussian."""
    def __init__(self, x, y):
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)

    def get_xy(self):
        return self.x, self.y

    def get_y(self, xq=None):
        if xq is None:
            return self.y
        return np.interp(xq, self.x, self.y, left=0.0, right=0.0)


class _FakeIcurve:
    def __init__(self, x, y):
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)

    def get_xy(self):
        return self.x, self.y


class _FakeDecomp:
    """Minimal decomposition consumed by optimize_uv_decomposition."""
    def __init__(self, uv_x, uv_y, mapping, xr_ccurves):
        self.uv_icurve = _FakeIcurve(uv_x, uv_y)
        self.mapping = mapping
        self.xr_ccurves = xr_ccurves
        self.num_components = len(xr_ccurves)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gaussian(x, center, sigma, amp):
    return amp * np.exp(-0.5 * ((x - center) / sigma) ** 2)


def _build_two_comp(true_scales=(0.3, 0.7)):
    """Two well-separated Gaussians; identity XR→UV mapping."""
    xr_frames = np.arange(400, 1001, dtype=float)
    uv_frames = np.arange(400, 1001, dtype=float)
    xr0 = _gaussian(xr_frames, center=550, sigma=30, amp=0.01)
    xr1 = _gaussian(xr_frames, center=750, sigma=40, amp=0.02)
    uv_y = true_scales[0] * xr0 + true_scales[1] * xr1
    mapping = _FakeMapping(slope=1.0, intercept=0.0)
    xr_ccurves = [_FakeXrCurve(xr_frames, xr0), _FakeXrCurve(xr_frames, xr1)]
    decomp = _FakeDecomp(uv_frames, uv_y, mapping, xr_ccurves)
    return decomp, xr_ccurves, list(true_scales)


# ---------------------------------------------------------------------------
# Patch helper: swap UvComponentCurve to a thin stand-in so the test never
# needs molass-legacy imports.
# ---------------------------------------------------------------------------

class _ThinUvCurve:
    """Replaces UvComponentCurve: scale * xr_ccurve.get_y(mapping.inv(x))."""
    def __init__(self, x, mapping, xr_ccurve, scale):
        self._x = np.asarray(x)
        self._mapping = mapping
        self._xr = xr_ccurve
        self.scale = scale

    def get_y(self):
        xr_frames = self._mapping.inv(self._x)
        return self.scale * self._xr.get_y(xr_frames)


import sys
import types as _types

def _patch_uvc(monkeypatch):
    """Inject _ThinUvCurve into sys.modules so the from-import inside the fn works."""
    import molass.SEC.Models.UvOptimizer as _mod
    fake_mod = _types.ModuleType('molass.SEC.Models.UvComponentCurve')
    fake_mod.UvComponentCurve = _ThinUvCurve
    orig = sys.modules.get('molass.SEC.Models.UvComponentCurve')
    sys.modules['molass.SEC.Models.UvComponentCurve'] = fake_mod

    def _restore():
        if orig is not None:
            sys.modules['molass.SEC.Models.UvComponentCurve'] = orig
        elif 'molass.SEC.Models.UvComponentCurve' in sys.modules:
            del sys.modules['molass.SEC.Models.UvComponentCurve']

    return _mod, _restore


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_physics_initial_scales_close_to_truth(monkeypatch):
    """Physics-based initial scales should be close to the true UV/XR ratios."""
    decomp, xr_ccurves, true_scales = _build_two_comp(true_scales=(0.3, 0.7))

    _mod, restore = _patch_uvc(monkeypatch)
    captured_initial = []
    orig_minimize = _mod.minimize

    def _mock_minimize(objective, x0, bounds=None, **kw):
        captured_initial.extend(x0[2:])
        return orig_minimize(objective, x0, bounds=bounds, **kw)

    monkeypatch.setattr(_mod, 'minimize', _mock_minimize)

    try:
        _mod.optimize_uv_decomposition(decomp, xr_ccurves)
    finally:
        restore()

    assert len(captured_initial) == 2
    for s_init, s_true in zip(captured_initial, true_scales):
        assert abs(s_init - s_true) / s_true < 0.10, (
            f"Initial scale {s_init:.4f} is not within 10% of true {s_true:.4f}"
        )


def test_converged_scales_close_to_truth(monkeypatch):
    """Optimizer should converge to the true scales for well-separated components."""
    decomp, xr_ccurves, true_scales = _build_two_comp(true_scales=(0.3, 0.7))

    _mod, restore = _patch_uvc(monkeypatch)
    try:
        uv_ccurves = _mod.optimize_uv_decomposition(decomp, xr_ccurves)
    finally:
        restore()

    converged_scales = [c.scale for c in uv_ccurves]
    for s_conv, s_true in zip(converged_scales, true_scales):
        assert abs(s_conv - s_true) / s_true < 0.05, (
            f"Converged scale {s_conv:.4f} is not within 5% of true {s_true:.4f}"
        )


def test_debug_output_printed(capsys):
    """debug=True should print [UV] initial_guess and [UV] converged lines.

    Uses the real UvComponentCurve (no patching) because debug=True triggers
    importlib.reload() which requires a real module spec.
    """
    from molass.SEC.Models.UvOptimizer import optimize_uv_decomposition
    decomp, xr_ccurves, _ = _build_two_comp()
    optimize_uv_decomposition(decomp, xr_ccurves, debug=True)

    out = capsys.readouterr().out
    assert '[UV] initial_guess:' in out, f"Missing initial_guess line: {out!r}"
    assert '[UV] converged:' in out, f"Missing converged line: {out!r}"
    assert 'scales=' in out
    assert 'residual_rms=' in out


def test_no_debug_output_by_default(monkeypatch, capsys):
    """Without debug=True, no [UV] lines should be printed."""
    decomp, xr_ccurves, _ = _build_two_comp()
    _mod, restore = _patch_uvc(monkeypatch)
    try:
        _mod.optimize_uv_decomposition(decomp, xr_ccurves)
    finally:
        restore()

    out = capsys.readouterr().out
    assert '[UV]' not in out, f"Unexpected [UV] output without debug=True: {out!r}"
