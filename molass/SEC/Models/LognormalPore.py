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