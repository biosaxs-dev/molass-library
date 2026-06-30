"""
tests/specific/300_SEC_Models/test_050_lkm_linear.py

Basic sanity tests for molass.SEC.Models.LkmLinear.lkm_pdf.

Column parameters (same as experiments 19g/19h):
  Pe=500, t0=2.0, k_MT=1.6667, R=4.0  → t_R=8.0
"""
import numpy as np
import pytest
from molass.SEC.Models.LkmLinear import lkm_pdf


# ── shared test grid ──────────────────────────────────────────────────────────
T  = np.linspace(0.05, 25.0, 4000)

# True column parameters (from 19g/19h STLC reference simulation)
PE    = 500.0
T0    = 2.0
K_MT  = 1.6667
R     = 4.0
T_R   = T0 * R   # = 8.0


def test_normalization():
    """Integral of the PDF over a wide time range should be close to 1."""
    y    = lkm_pdf(T, Pe=PE, t0=T0, k_MT=K_MT, R=R)
    intg = np.trapezoid(y, T)
    assert abs(intg - 1.0) < 0.01, f"Integral = {intg:.4f}, expected ≈ 1.0"


def test_peak_location():
    """Peak (mode) should be close to but not above t_R = t0 * R."""
    y      = lkm_pdf(T, Pe=PE, t0=T0, k_MT=K_MT, R=R)
    t_peak = T[np.argmax(y)]
    # mode < mean for a right-skewed distribution; allow 20% below t_R
    assert t_peak < T_R, f"Peak {t_peak:.3f} should be below t_R={T_R}"
    assert t_peak > T_R * 0.80, f"Peak {t_peak:.3f} is too far below t_R={T_R}"


def test_non_negative():
    """PDF values must be non-negative everywhere."""
    y = lkm_pdf(T, Pe=PE, t0=T0, k_MT=K_MT, R=R)
    # FftInvPdf clamps FFT output but the spline may interpolate to tiny
    # negative values near machine epsilon; allow a small absolute tolerance.
    assert np.all(y >= -1e-6), f"PDF has significant negative values: min={y.min():.3e}"


def test_timescale_override():
    """Explicit timescale should give the same integral as automatic."""
    y_auto    = lkm_pdf(T, Pe=PE, t0=T0, k_MT=K_MT, R=R)
    ts        = 80.0 / (T0 * R)
    y_manual  = lkm_pdf(T, Pe=PE, t0=T0, k_MT=K_MT, R=R, timescale=ts)
    np.testing.assert_allclose(y_auto, y_manual, rtol=1e-6)


def test_pe_sensitivity():
    """Lower Pe → broader peak (higher variance), same normalization."""
    y_hi = lkm_pdf(T, Pe=1000, t0=T0, k_MT=K_MT, R=R)
    y_lo = lkm_pdf(T, Pe=100,  t0=T0, k_MT=K_MT, R=R)
    # Peak of high-Pe PDF should be taller (narrower peak → higher maximum)
    assert y_hi.max() > y_lo.max(), "Higher Pe should give a taller (narrower) peak"
    # Both should integrate to ~1
    for Pe_val, y in [(1000, y_hi), (100, y_lo)]:
        intg = np.trapezoid(y, T)
        assert abs(intg - 1.0) < 0.02, f"Pe={Pe_val}: integral={intg:.4f}"
