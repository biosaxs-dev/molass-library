"""
SEC.Models.SdmMonoPore.py
"""
import numpy as np
from molass.MathUtils.FftUtils import FftInvPdf

def sdm_monopore_cf(w, npi, tpi, N0, t0):
    Z = npi*(1/(1 - 1j*w*tpi) - 1) + 1j*w*t0
    return np.exp(Z + Z**2/(2*N0))

sdm_monopore_pdf_impl = FftInvPdf(sdm_monopore_cf)

DEFAULT_TIMESCALE = 0.25    # 0.1 for FER_OA
N0 = 14400.0    # 48000*0.3 (30cm) or (t0/σ0)**2, see meeting document 20221104/index.html 

def sdm_monopore_pdf(x, npi, tpi, N0, t0, timescale=DEFAULT_TIMESCALE):
    """
    PDF of the SDM (Standard Dispersive Model) for a monoporous stationary phase.

    Uses FFT-based characteristic function inversion via FftInvPdf.

    Parameters
    ----------
    x : array_like
        Time array (physical time units).
    npi : float
        Mean number of pore entries (Poisson parameter of the compound-Poisson
        process).  Physical mapping: npi ≈ F * a  (phase ratio × Henry coefficient).
    tpi : float
        Mean pore residence time per visit (scale of the exponential distribution).
        Physical mapping: tpi ≈ t0 / npi  in the k → ∞ LKM limit.
    N0 : float
        Mobile-phase plate count (controls Gaussian peak width; σ_mobile ≈ t0/√N0).
    t0 : float
        Mean mobile-phase transit time (dead time).  Fix at the known dead time
        when fitting; do not use as a free parameter unless the dead time is unknown.
    timescale : float, optional
        Time rescaling factor for the internal FFT grid (default 0.25).
        The FFT grid spans [0, 1024) in scaled coordinates.  The peak should land
        well within [10, 900] on the scaled grid to avoid edge artefacts.
        Rule of thumb:  timescale ≈ 80 / t_R
          - SEC-SAXS data (t_R ~ 0.2–2 s): default 0.25 is appropriate.
          - General chromatography (t_R ~ 8): use timescale=10.0.

    Returns
    -------
    ndarray
        Normalised PDF evaluated at each point in ``x``  (integral ≈ 1).
        Multiply by the pulse area (cinj × t_inj) to obtain absolute
        concentration units.

    Notes
    -----
    Non-identifiability of npi and tpi
        Only the product ``npi * tpi`` (= mean total pore retention time ≈ F*a*t0)
        is tightly constrained by the peak position.  The individual values affect
        peak shape (variance and skewness), but many ``(npi, tpi)`` pairs with the
        same product give nearly indistinguishable peaks for typical chromatographic
        data.  When fitting, report ``npi * tpi`` as the physically meaningful
        quantity rather than npi or tpi individually.
    """
    return timescale*sdm_monopore_pdf_impl(timescale*x, npi, timescale*tpi, N0, timescale*t0)

def sdm_monopore_gamma_cf(w, npi, k, theta, N0, t0):
    """
    Gamma-distributed residence times with mobile phase dispersion.
    
    Parameters:
    -----------
    w : array
        Frequency array
    npi : float
        Mean number of pore entries (Poisson parameter)
    k : float
        Gamma shape parameter (k=1 recovers exponential)
    theta : float
        Gamma scale parameter (mean residence = k*theta)
    N0 : float
        Plate number (mobile phase dispersion)
    t0 : float
        Mean mobile phase time
    
    Returns:
    --------
    CF : complex array
        Characteristic function
        
    Notes:
    ------
    - Exponential: CF = 1/(1 - iω*τ)
    - Gamma: CF = (1 - iω*θ)^(-k)
    - For k=1, θ=τ: Gamma → Exponential
    """
    # Gamma CF for single pore visit: (1 - iω*θ)^(-k)
    # CPP with Gamma jumps: exp[n*(CF - 1)]
    Z = npi*((1 - 1j*w*theta)**(-k) - 1) + 1j*w*t0
    return np.exp(Z + Z**2/(2*N0))

# Create PDF calculator
sdm_monopore_gamma_pdf_impl = FftInvPdf(sdm_monopore_gamma_cf)

def sdm_monopore_gamma_pdf(x, npi, k, theta, N0, t0, timescale=DEFAULT_TIMESCALE):
    """Wrapper with timescale normalization"""
    return timescale*sdm_monopore_gamma_pdf_impl(
        timescale*x, npi, k, timescale*theta, N0, timescale*t0
    )