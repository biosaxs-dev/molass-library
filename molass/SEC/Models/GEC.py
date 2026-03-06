"""
    SEC.Models.GEC.py
"""
import numpy as np
from scipy.special import iv, ive

def gec_monopore_pdf(t, np_, tp_):
    return iv(1, np.sqrt(4*np_*t/tp_)) * np.sqrt(np_/(t*tp_)) * np.exp(-t/tp_-np_)

def robust_gec_monopore_pdf(t, np_, tp_):
    # Bessel functions in Python that work with large exponents
    # https://stackoverflow.com/questions/13726464/bessel-functions-in-python-that-work-with-large-exponents
    #
    # iv(1, np.sqrt(4*np_*t/tp_)) * np.sqrt(np_/(t*tp_)) * np.exp(-t/tp_-np_)
    #
    # ive(v, z) = iv(v, z) * exp(-abs(z.real))
    # iv(v, sq) = ive(v, sq) * exp(sq)

    # val = single_pore_pdf(t, np_, tp_)
    sq = np.sqrt(4*np_*t/tp_)
    val = ive(1, sq) * np.sqrt(np_/(t*tp_)) * np.exp(sq -t/tp_ -np_)
    isnan_val = np.isnan(val)
    val[isnan_val] = 0
    return val

from molass_legacy.SecTheory.SecPDF import FftInvPdf
def gec_monopore_cf(s, np_, tp_):
    # Characteristic function of the GEC monopore model
    return np.exp(np_ * (1/(1 - 1j * tp_ * s) - 1))
 
gec_monopore_numerical_inversion_pdf = FftInvPdf(gec_monopore_cf)