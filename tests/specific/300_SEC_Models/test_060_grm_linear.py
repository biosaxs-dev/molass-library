"""
tests/specific/300_SEC_Models/test_060_grm_linear.py

Sanity tests for molass.SEC.Models.GrmLinear.grm_pdf.

Parameters follow the consistency-check notebook (27b):
  Pe=400, t0=5.0, R=3.0, eps=0.4, F=1.5, k_MT=2.0/min
  R_p=0.004 cm, D_eff=1e3 cm²/min (film-only limit)
  k_ext = k_MT * R_p * R / (3 * F) = 0.00533 cm/min

Analytical variance (film-only, large D_eff):
  σ²_GRM = 2*t0²*R²/Pe + 2*t0*(R−1)²/(R * k_MT_eff)
  k_MT_eff = 3*F*k_ext / (R_p*R)
"""
import numpy as np
import pytest
from molass.SEC.Models.GrmLinear import grm_pdf
from molass.SEC.Models.LkmLinear import lkm_pdf
from molass.SEC.Models.EdmLinear import edm_pdf


# ── shared test grid ──────────────────────────────────────────────────────────
T   = np.linspace(0.1, 50.0, 4000)

PE    = 400.0
T0    = 5.0
EPS   = 0.4
F     = (1 - EPS) / EPS       # = 1.5
R     = 3.0
A     = (R - 1) / F            # Henry coefficient ≈ 1.333
EPS_P = 0.0
A_STAR = EPS_P + (1 - EPS_P) * A   # = A (non-porous particles)
R_P   = 0.004    # cm
D_EFF = 1e3      # cm²/min  (film-only limit)
K_MT  = 2.0      # min⁻¹  (target k_MT_eff)
K_EXT = K_MT * R_P * R / (3 * F)  # ≈ 0.00533 cm/min

T_R = T0 * R    # = 15.0 min

# Analytical moments (Qamar 2014 Table 1, film-only limit)
K_MT_EFF  = 3 * F * K_EXT / (R_P * R)   # = K_MT = 2.0
VAR_AXIAL = 2 * T0**2 * R**2 / PE
VAR_THEORY = VAR_AXIAL + 2 * T0 * (R - 1)**2 / (R * K_MT_EFF)


def test_normalization():
    """Integral of the PDF should be close to 1."""
    y    = grm_pdf(T, PE, T0, K_EXT, R_P, D_EFF, A_STAR, F)
    intg = np.trapezoid(y, T)
    assert abs(intg - 1.0) < 0.01, f"Integral = {intg:.4f}, expected ≈ 1.0"


def test_mean():
    """Numerical mean μ₁ should equal t0 * R_eff within 0.1%."""
    y   = grm_pdf(T, PE, T0, K_EXT, R_P, D_EFF, A_STAR, F)
    mu1 = np.trapezoid(T * y, T) / np.trapezoid(y, T)
    assert abs(mu1 - T_R) / T_R < 0.001, f"μ₁={mu1:.4f}, expected {T_R:.4f}"


def test_variance():
    """Numerical σ² should match Qamar 2014 Table 1 formula within 0.5%."""
    y   = grm_pdf(T, PE, T0, K_EXT, R_P, D_EFF, A_STAR, F)
    mu1 = np.trapezoid(T * y, T) / np.trapezoid(y, T)
    var = np.trapezoid((T - mu1)**2 * y, T) / np.trapezoid(y, T)
    err = abs(var - VAR_THEORY) / VAR_THEORY
    assert err < 0.005, f"σ²={var:.4f}, theory={VAR_THEORY:.4f}, err={err*100:.2f}%"


def test_non_negative():
    """PDF must be non-negative everywhere."""
    y = grm_pdf(T, PE, T0, K_EXT, R_P, D_EFF, A_STAR, F)
    assert np.all(y >= -1e-6), f"PDF has significant negative values: min={y.min():.3e}"


def test_width_hierarchy():
    """Width ordering: EDM < GRM < LKM at the same effective k_MT.

    Uses the moment-matching k_MT_LKM = R/(R-1) * k_MT_eff so all three
    models have the same σ² — then checks that GRM is between EDM and the
    *unmatched* LKM.
    """
    def _var(y):
        mu = np.trapezoid(T * y, T) / np.trapezoid(y, T)
        return np.trapezoid((T - mu)**2 * y, T) / np.trapezoid(y, T)

    y_edm = edm_pdf(T, PE, T0, R)
    y_grm = grm_pdf(T, PE, T0, K_EXT, R_P, D_EFF, A_STAR, F)
    y_lkm = lkm_pdf(T, PE, T0, K_MT, R)

    var_edm = _var(y_edm)
    var_grm = _var(y_grm)
    var_lkm = _var(y_lkm)

    assert var_edm < var_grm, f"EDM σ²={var_edm:.4f} should be < GRM σ²={var_grm:.4f}"
    assert var_grm < var_lkm, f"GRM σ²={var_grm:.4f} should be < LKM σ²={var_lkm:.4f}"


def test_moment_matching_with_lkm():
    """Moment-matched GRM and LKM should have equal σ² (Qamar App C).

    k_MT_LKM = R/(R−1) * k_MT_eff  → σ²_LKM = σ²_GRM
    """
    k_MT_matched = R / (R - 1) * K_MT_EFF   # = 3.0 min⁻¹

    def _var(y):
        mu = np.trapezoid(T * y, T) / np.trapezoid(y, T)
        return np.trapezoid((T - mu)**2 * y, T) / np.trapezoid(y, T)

    y_grm      = grm_pdf(T, PE, T0, K_EXT, R_P, D_EFF, A_STAR, F)
    y_lkm_match = lkm_pdf(T, PE, T0, k_MT_matched, R)

    var_grm = _var(y_grm)
    var_lkm = _var(y_lkm_match)

    assert abs(var_grm - var_lkm) < 0.001, (
        f"Moment-matched: σ²_GRM={var_grm:.4f} vs σ²_LKM={var_lkm:.4f}, "
        f"Δ={abs(var_grm-var_lkm):.4f}"
    )


def test_timescale_override():
    """Explicit timescale should match auto timescale."""
    R_eff    = 1.0 + F * A_STAR
    ts       = 80.0 / (T0 * R_eff)
    y_auto   = grm_pdf(T, PE, T0, K_EXT, R_P, D_EFF, A_STAR, F)
    y_manual = grm_pdf(T, PE, T0, K_EXT, R_P, D_EFF, A_STAR, F, timescale=ts)
    np.testing.assert_allclose(y_auto, y_manual, rtol=1e-6)
