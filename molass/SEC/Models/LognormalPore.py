"""
SEC.Models.LognormalPore.py
"""
import numpy as np
from scipy.stats import lognorm
from molass.MathUtils.IntegrateUtils import complex_quadrature_vec
from molass.MathUtils.FftUtils import FftInvPdf

def compute_mode(mu, sigma):
    return np.exp(mu - sigma**2)

def compute_stdev(mu, sigma):
    return np.sqrt((np.exp(sigma**2) - 1)*np.exp(2*mu + sigma**2))

def Ksec(Rg, r, m):
    return np.power(1 - min(1, Rg/r), m)

def distribution_func(r, mu, sigma):
    return lognorm.pdf(r, sigma, scale=np.exp(mu))

def gec_lognormal_pore_integrand_impl(r, w, N, T, me, mp, mu, sigma, Rg):
    return distribution_func(r, mu, sigma)*N*Ksec(Rg, r, me)*(1/(1 - w*1j*T*Ksec(Rg, r, mp)) - 1)

PORESIZE_INTEG_LIMIT = 600  # changing this value to 600 once seemed harmful to the accuracy of numerical integration

def gec_lognormal_pore_cf(w, N, T, me, mp, mu, sigma, Rg, x0, const_rg_limit=False):
    if const_rg_limit:
        max_rg = PORESIZE_INTEG_LIMIT
    else:
        mode = compute_mode(mu, sigma)
        stdev = compute_stdev(mu, sigma)
        max_rg = min(PORESIZE_INTEG_LIMIT, mode + 5*stdev)

    # note that gec_lognormal_pore_integrand_impl is a vector function because w is a vector
    integrated = complex_quadrature_vec(lambda r: gec_lognormal_pore_integrand_impl(r, w, N, T, me, mp, mu, sigma, Rg), Rg, max_rg)[0]
    return np.exp(integrated + 1j*w*x0)     # + 1j*w*x0 may not be correct. reconsider

gec_lognormal_pore_pdf_impl = FftInvPdf(gec_lognormal_pore_cf)

def gec_lognormal_pore_pdf(x, scale, N, T, me, mp, mu, sigma, Rg, x0):
    return scale*gec_lognormal_pore_pdf_impl(x - x0, N, T, me, mp, mu, sigma, Rg, 0)  # not always the same as below
    # return scale*gec_lognormal_pore_pdf_impl(x, N, T, me, mp, mu, sigma, Rg, x0)

# ============================================================================
# SDM Extensions: Adding Mobile Phase Dispersion (Brownian component)
# 
# The following implementations were proposed by GitHub Copilot (Claude Sonnet 4.5)
# on December 27, 2025, extending the GEC lognormal pore model with:
# 1. Mobile phase dispersion (SDM framework)
# 2. Gamma-distributed residence times (kinetic heterogeneity)
# ============================================================================

def sdm_lognormal_pore_cf(w, N, T, me, mp, mu, sigma, Rg, N0, t0, const_rg_limit=False):
    """
    SDM with lognormal pore distribution and exponential residence time.
    
    Adds mobile phase dispersion (Brownian term) to GEC lognormal model.
    
    Parameters
    ----------
    w : array
        Frequency array
    N : float
        Pore interaction scale parameter
    T : float
        Residence time scale parameter
    me : float
        Pore entry exponent
    mp : float
        Pore residence exponent
    mu : float
        Log-mean of pore size distribution
    sigma : float
        Log-std of pore size distribution
    Rg : float
        Molecule radius of gyration (lower integration limit)
    N0 : float
        Plate number (mobile phase dispersion parameter)
    t0 : float
        Mobile phase hold-up time (drift term)
    const_rg_limit : bool, optional
        Use constant integration limit (default: False)
    
    Returns
    -------
    complex array
        Characteristic function values
        
    Notes
    -----
    CF structure: φ(ω) = exp(Z + Z²/(2*N0))
    where Z = [lognormal pore integral] + iω*t0
    
    The Z²/(2*N0) term represents axial dispersion in mobile phase.
    """
    if const_rg_limit:
        max_rg = PORESIZE_INTEG_LIMIT
    else:
        mode = compute_mode(mu, sigma)
        stdev = compute_stdev(mu, sigma)
        max_rg = min(PORESIZE_INTEG_LIMIT, mode + 5*stdev)

    # Integrate over lognormal pore distribution (same as GEC)
    integrated = complex_quadrature_vec(
        lambda r: gec_lognormal_pore_integrand_impl(r, w, N, T, me, mp, mu, sigma, Rg), 
        Rg, max_rg
    )[0]
    
    # Add drift term to get Z
    Z = integrated + 1j*w*t0
    
    # Add Brownian dispersion term
    return np.exp(Z + Z**2/(2*N0))

sdm_lognormal_pore_pdf_impl = FftInvPdf(sdm_lognormal_pore_cf)

def sdm_lognormal_pore_pdf(x, scale, N, T, me, mp, mu, sigma, Rg, N0, t0):
    """
    PDF for SDM with lognormal pore distribution.
    
    Parameters
    ----------
    x : array
        Time points
    scale : float
        Amplitude scaling factor
    N, T, me, mp : float
        Pore interaction parameters
    mu, sigma : float
        Lognormal distribution parameters
    Rg : float
        Molecule radius of gyration
    N0 : float
        Plate number
    t0 : float
        Mobile phase time
    
    Returns
    -------
    array
        Probability density values
    """
    return scale*sdm_lognormal_pore_pdf_impl(x - t0, N, T, me, mp, mu, sigma, Rg, N0, 0)

# ============================================================================
# Gamma Residence Time Extensions
# ============================================================================

def sdm_lognormal_pore_gamma_integrand_impl(r, w, N, T, k, me, mp, mu, sigma, Rg):
    """
    Integrand for SDM lognormal pore with Gamma-distributed residence times.
    
    Replaces exponential residence time with Gamma distribution.
    
    Parameters
    ----------
    r : float or array
        Pore radius (integration variable)
    w : array
        Frequency array
    N : float
        Pore interaction scale
    T : float
        Residence time scale (theta parameter for Gamma)
    k : float
        Gamma shape parameter (k=1 recovers exponential)
    me, mp : float
        Exponents for entry and residence
    mu, sigma : float
        Lognormal parameters
    Rg : float
        Molecule radius of gyration
    
    Returns
    -------
    complex array
        Integrand values
        
    Notes
    -----
    Gamma CF for single visit: (1 - iω*θ)^(-k)
    For k=1, recovers exponential case.
    """
    # Lognormal PDF for pore size
    g_r = distribution_func(r, mu, sigma)
    
    # Number of pore entries (size-dependent)
    n_pore = N * Ksec(Rg, r, me)
    
    # Gamma characteristic function term
    # θ = T * Ksec(Rg, r, mp) - scale parameter depends on pore size
    theta_r = T * Ksec(Rg, r, mp)
    
    # CF of Gamma(k, θ): (1 - iω*θ)^(-k)
    # Compound Poisson term: n * (φ - 1)
    gamma_cf_term = (1 - 1j*w*theta_r)**(-k) - 1
    
    return g_r * n_pore * gamma_cf_term

def sdm_lognormal_pore_gamma_cf(w, N, T, k, me, mp, mu, sigma, Rg, N0, t0, const_rg_limit=False):
    """
    SDM with lognormal pore distribution and Gamma-distributed residence times.
    
    Most general model: combines pore size heterogeneity (lognormal) with
    residence time heterogeneity (Gamma) and mobile phase dispersion.
    
    Parameters
    ----------
    w : array
        Frequency array
    N : float
        Pore interaction scale parameter
    T : float
        Residence time scale parameter (Gamma scale θ)
    k : float
        Gamma shape parameter (k=1 → exponential, k>1 → less dispersed)
    me : float
        Pore entry exponent
    mp : float
        Pore residence exponent
    mu : float
        Log-mean of pore size distribution
    sigma : float
        Log-std of pore size distribution
    Rg : float
        Molecule radius of gyration
    N0 : float
        Plate number (mobile phase dispersion)
    t0 : float
        Mobile phase hold-up time
    const_rg_limit : bool, optional
        Use constant integration limit
    
    Returns
    -------
    complex array
        Characteristic function values
        
    Notes
    -----
    This is the most comprehensive SEC model:
    - Lognormal pore size distribution (structural heterogeneity)
    - Gamma residence time distribution (kinetic heterogeneity)
    - Mobile phase dispersion (Brownian component)
    - Size exclusion effects (Ksec with Rg)
    
    **CF structure**::
    
        φ(ω) = exp[Z + Z²/(2*N0)]
        Z = iω*t0 + ∫_{Rg}^∞ L_{μ,σ}(r) * n_r * ((1 - iω*τ_r)^{-k} - 1) dr
    
    **Moment formulas** (from meeting doc 2026-01-19):
    
        M1 (mean) = t0 + k * ∫_{Rg}^∞ L_{μ,σ}(r) * n_r * τ_r dr
    
        M2~ (variance) = k*(k+1) * ∫_{Rg}^∞ L_{μ,σ}(r) * n_r * τ_r² dr
                         + M1² / N0
    
    where n_r = N * Ksec(Rg, r, me) and τ_r = T * Ksec(Rg, r, mp).
    
    The variance has two terms:
    - Altering-zone term: k*(k+1) * ∫... (pore residence heterogeneity)
    - Dispersive term: M1² / N0 (mobile phase Brownian broadening)
    
    For special cases:
    - k=1: Reduces to sdm_lognormal_pore_cf (exponential residence)
    - N0→∞: Reduces to GEC with Gamma residence
    - σ→0: Reduces to sdm_monopore_gamma_cf (single pore size)
    """
    if const_rg_limit:
        max_rg = PORESIZE_INTEG_LIMIT
    else:
        mode = compute_mode(mu, sigma)
        stdev = compute_stdev(mu, sigma)
        max_rg = min(PORESIZE_INTEG_LIMIT, mode + 5*stdev)

    # Integrate over lognormal pore distribution with Gamma residence
    integrated = complex_quadrature_vec(
        lambda r: sdm_lognormal_pore_gamma_integrand_impl(r, w, N, T, k, me, mp, mu, sigma, Rg), 
        Rg, max_rg
    )[0]
    
    # Add drift term
    Z = integrated + 1j*w*t0
    
    # Add Brownian dispersion term
    return np.exp(Z + Z**2/(2*N0))

sdm_lognormal_pore_gamma_pdf_impl = FftInvPdf(sdm_lognormal_pore_gamma_cf)

def sdm_lognormal_pore_gamma_pdf(x, scale, N, T, k, me, mp, mu, sigma, Rg, N0, t0):
    """
    PDF for SDM with lognormal pore distribution and Gamma residence times.
    
    Parameters
    ----------
    x : array
        Time points
    scale : float
        Amplitude scaling factor
    N, T : float
        Pore interaction and time scale parameters
    k : float
        Gamma shape parameter
    me, mp : float
        Pore entry and residence exponents
    mu, sigma : float
        Lognormal distribution parameters
    Rg : float
        Molecule radius of gyration
    N0 : float
        Plate number
    t0 : float
        Mobile phase time
    
    Returns
    -------
    array
        Probability density values
        
    Examples
    --------
    >>> # Fit SEC-SAXS data with full model
    >>> t = np.linspace(0, 300, 1000)
    >>> pdf = sdm_lognormal_pore_gamma_pdf(
    ...     t, scale=1.0, N=100, T=2.0, k=1.5,
    ...     me=2.0, mp=2.0, mu=4.2, sigma=0.3,
    ...     Rg=50, N0=14400, t0=5.0
    ... )
    """
    return scale*sdm_lognormal_pore_gamma_pdf_impl(x - t0, N, T, k, me, mp, mu, sigma, Rg, N0, 0)

# ============================================================================
# Fast Gauss-Legendre Versions (for optimizer use)
#
# Replace adaptive quad_vec with fixed Gauss-Legendre quadrature and fully
# vectorized numpy operations.  Typical speedup: 50-100x per PDF call.
# ============================================================================

def sdm_lognormal_pore_gamma_cf_fast(w, N, T, k, me, mp, mu, sigma, Rg, N0, t0, n_quad=64):
    """Vectorized Gauss-Legendre version of sdm_lognormal_pore_gamma_cf."""
    mode = compute_mode(mu, sigma)
    stdev = compute_stdev(mu, sigma)
    max_rg = min(PORESIZE_INTEG_LIMIT, mode + 5*stdev)

    if max_rg <= Rg:
        Z = 1j * w * t0
        return np.exp(Z + Z**2 / (2 * N0))

    # Gauss-Legendre nodes/weights mapped to [Rg, max_rg]
    nodes, weights = np.polynomial.legendre.leggauss(n_quad)
    half = 0.5 * (max_rg - Rg)
    mid  = 0.5 * (max_rg + Rg)
    r  = half * nodes + mid       # (n_quad,)
    wt = half * weights           # (n_quad,)

    # Integrand components at all quadrature nodes
    g = lognorm.pdf(r, sigma, scale=np.exp(mu))   # (n_quad,)
    ratio = np.minimum(1.0, Rg / r)               # (n_quad,)
    n_pore = N * (1 - ratio)**me                   # (n_quad,)
    theta  = T * (1 - ratio)**mp                   # (n_quad,)

    # Gamma CF: (1 - iw*theta)^(-k) - 1
    # Broadcast: w (n_w,1) × theta (1,n_quad) → (n_w, n_quad)
    gamma_term = (1 - 1j * w[:, None] * theta[None, :])**(-k) - 1

    # Weighted sum over quadrature nodes
    coeffs = g * n_pore * wt                       # (n_quad,)
    integrated = gamma_term @ coeffs               # (n_w,)

    Z = integrated + 1j * w * t0
    return np.exp(Z + Z**2 / (2 * N0))

_sdm_lognormal_pore_gamma_pdf_fast_impl = FftInvPdf(sdm_lognormal_pore_gamma_cf_fast)

def sdm_lognormal_pore_gamma_pdf_fast(x, scale, N, T, k, me, mp, mu, sigma, Rg, N0, t0):
    """Fast version of sdm_lognormal_pore_gamma_pdf using Gauss-Legendre quadrature."""
    return scale * _sdm_lognormal_pore_gamma_pdf_fast_impl(x - t0, N, T, k, me, mp, mu, sigma, Rg, N0, 0)


# --------------------------------------------------------------------------
# Analytical moments of SDM lognormal-pore gamma distribution
# --------------------------------------------------------------------------
# The full elution PDF is expensive to evaluate (~10 ms for len(x)=800).
# For initial parameter estimation by moment matching we only need the
# first two moments (M1, Variance), which can be computed analytically by
# integrating over the pore-size distribution. The integral is evaluated
# by 64-point Gauss-Legendre quadrature on [Rg, max_rg].
#
# Per-call cost: ~50 us (≈200x faster than the full PDF). This makes
# moment-matching viable inside an inner optimization loop.
#
# See molass-researcher 13v_moment_matching_strategy notebook for the
# benchmark and derivation. Issue #113.

_GL64_NODES, _GL64_WEIGHTS = np.polynomial.legendre.leggauss(64)
_LOG_2PI_HALF = 0.5 * np.log(2.0 * np.pi)

def _lognorm_pdf_fast(r, mu, sigma):
    """Hand-rolled lognormal PDF (~6x faster than scipy.stats.lognorm.pdf,
    bit-identical to ~1e-16 relative error)."""
    z = (np.log(r) - mu) / sigma
    return np.exp(-0.5 * z * z - _LOG_2PI_HALF) / (r * sigma)

def sdm_lognormal_model_moments(rg, N, T, N0, t0, k, mu, sigma, me=1.5, mp=1.5):
    """Compute (M1, Variance) of the SDM lognormal-pore gamma elution model.

    For a single component with radius of gyration ``rg``, the residence-time
    distribution is gamma with shape ``k`` and per-pore mean ``n(r)·tau(r)``,
    weighted by the lognormal pore-size density L(r; mu, sigma).

    Formulas:
        M1  = t0 + k * I1
        Var = k * (k + 1) * I2 + M1^2 / N0
    where
        I1 = integral over r in [rg, max_rg] of L(r) * n(r) * tau(r) dr
        I2 = integral over r in [rg, max_rg] of L(r) * n(r) * tau(r)^2 dr
        n(r)   = N * (1 - rg/r)^me
        tau(r) = T * (1 - rg/r)^mp

    The variance formula uses the second *raw* moment of the per-pore Gamma
    distribution (k*(k+1)*theta^2), as appropriate for the compound-Poisson
    structure of the SDM model.

    Parameters
    ----------
    rg : float
        Radius of gyration of the component (Å).
    N, T : float
        SDM column parameters (per-pore plate count and residence time).
    N0 : float
        Mobile-phase plate number (governs Gaussian dispersion).
    t0 : float
        Dead time / column offset.
    k : float
        Gamma shape parameter for residence-time distribution.
    mu, sigma : float
        Lognormal pore-size distribution parameters.
    me, mp : float, optional
        SEC partition exponents (default 1.5).

    Returns
    -------
    (M1, Var) : tuple of float
        First moment (mean) and central second moment (variance) of
        the elution profile.

    See Also
    --------
    sdm_lognormal_pore_gamma_pdf_fast : full elution PDF computation.
    """
    sigma2 = sigma * sigma
    mode = np.exp(mu - sigma2)
    stdev = np.exp(mu + 0.5 * sigma2) * np.sqrt(np.exp(sigma2) - 1.0)
    max_rg = min(PORESIZE_INTEG_LIMIT, mode + 5.0 * stdev)
    if max_rg <= rg:
        # All pores excluded: pure mobile-phase Gaussian at t0
        return t0, t0 * t0 / N0

    half = 0.5 * (max_rg - rg)
    mid  = 0.5 * (max_rg + rg)
    r  = half * _GL64_NODES + mid
    wt = half * _GL64_WEIGHTS

    g = _lognorm_pdf_fast(r, mu, sigma)
    ratio = np.minimum(1.0, rg / r)
    one_minus = 1.0 - ratio
    n_pore = N * one_minus**me
    theta  = T * one_minus**mp

    coeffs = g * n_pore * wt
    I1 = np.dot(coeffs, theta)
    I2 = np.dot(coeffs, theta * theta)

    M1 = t0 + k * I1
    Var = k * (k + 1.0) * I2 + M1 * M1 / N0
    return M1, Var