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