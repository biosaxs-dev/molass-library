"""
SEC.Models.LognormalPore.py
"""
import numpy as np
from scipy.stats import lognorm
from molass.MathUtils.IntegrateUtils import complex_quadrature_vec

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

"""
task:
- sdm_lognormal_pore_gamma_cf
- sdm_lognormal_pore_gamma_pdf
"""