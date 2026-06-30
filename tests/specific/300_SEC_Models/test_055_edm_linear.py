"""
tests/specific/300_SEC_Models/test_055_edm_linear.py

Sanity tests for molass.SEC.Models.EdmLinear.edm_pdf.

Parameters follow the consistency-check notebook (27b):
  Pe=400, t0=5.0, R=3.0  →  t_R=15.0, σ²=1.125 min²

Tests also verify the EDM < LKM width hierarchy.
"""
import numpy as np
import pytest
from molass.SEC.Models.EdmLinear import edm_pdf
from molass.SEC.Models.LkmLinear import lkm_pdf


# ── shared test grid ──────────────────────────────────────────────────────────
T   = np.linspace(0.1, 40.0, 4000)

PE  = 400.0
T0  = 5.0
R   = 3.0
T_R = T0 * R   # = 15.0

# Analytical variance: σ² = 2*t0²*R²/Pe
VAR_THEORY = 2 * T0**2 * R**2 / PE   # = 1.125 min²


def test_normalization():
    """Integral of the PDF should be close to 1."""
    y    = edm_pdf(T, Pe=PE, t0=T0, R=R)
    intg = np.trapezoid(y, T)
    assert abs(intg - 1.0) < 0.01, f"Integral = {intg:.4f}, expected ≈ 1.0"


def test_mean():
    """Numerical mean μ₁ should equal t0 * R within 0.1%."""
    y    = edm_pdf(T, Pe=PE, t0=T0, R=R)
    mu1  = np.trapezoid(x * y, T) if False else np.trapezoid(T * y, T) / np.trapezoid(y, T)
    assert abs(mu1 - T_R) / T_R < 0.001, f"μ₁={mu1:.4f}, expected {T_R:.4f}"


def test_variance():
    """Numerical σ² should match analytical 2*t0²*R²/Pe within 0.5%."""
    y    = edm_pdf(T, Pe=PE, t0=T0, R=R)
    mu1  = np.trapezoid(T * y, T) / np.trapezoid(y, T)
    var  = np.trapezoid((T - mu1)**2 * y, T) / np.trapezoid(y, T)
    err  = abs(var - VAR_THEORY) / VAR_THEORY
    assert err < 0.005, f"σ²={var:.4f}, theory={VAR_THEORY:.4f}, err={err*100:.2f}%"


def test_non_negative():
    """PDF must be non-negative everywhere."""
    y = edm_pdf(T, Pe=PE, t0=T0, R=R)
    assert np.all(y >= -1e-6), f"PDF has significant negative values: min={y.min():.3e}"


def test_narrower_than_lkm():
    """EDM must be narrower than LKM at the same Pe, t0, R.

    EDM σ² = 2t0²R²/Pe < LKM σ² = 2t0²R²/Pe + 2t0(R−1)/k_MT
    """
    k_MT = 2.0
    y_edm = edm_pdf(T, Pe=PE, t0=T0, R=R)
    y_lkm = lkm_pdf(T, Pe=PE, t0=T0, k_MT=k_MT, R=R)

    def _var(y):
        mu = np.trapezoid(T * y, T) / np.trapezoid(y, T)
        return np.trapezoid((T - mu)**2 * y, T) / np.trapezoid(y, T)

    var_edm = _var(y_edm)
    var_lkm = _var(y_lkm)
    assert var_edm < var_lkm, (
        f"EDM σ²={var_edm:.4f} should be < LKM σ²={var_lkm:.4f}"
    )


def test_timescale_override():
    """Explicit timescale should match auto timescale."""
    y_auto   = edm_pdf(T, Pe=PE, t0=T0, R=R)
    ts       = 80.0 / (T0 * R)
    y_manual = edm_pdf(T, Pe=PE, t0=T0, R=R, timescale=ts)
    np.testing.assert_allclose(y_auto, y_manual, rtol=1e-6)
