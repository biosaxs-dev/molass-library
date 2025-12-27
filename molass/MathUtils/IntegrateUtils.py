
"""
    MathUtils/IntegrateUtils.py
"""
import numpy as np
from scipy.integrate import quad, quad_vec

"""
copied from https://stackoverflow.com/questions/5965583/use-scipy-integrate-quad-to-integrate-complex-numbers
"""
def complex_quadrature(func, a, b, **kwargs):
    def real_func(x):
        return np.real(func(x))
    def imag_func(x):
        return np.imag(func(x))
    real_integral = quad(real_func, a, b, **kwargs)
    imag_integral = quad(imag_func, a, b, **kwargs)
    return (real_integral[0] + 1j*imag_integral[0], real_integral[1:], imag_integral[1:])

"""
quad_vec version
"""
def complex_quadrature_vec(func, a, b, **kwargs):
    def real_func(x):
        return np.real(func(x))
    def imag_func(x):
        return np.imag(func(x))
    real_integral = quad_vec(real_func, a, b, **kwargs)
    imag_integral = quad_vec(imag_func, a, b, **kwargs)
    return (real_integral[0] + 1j*imag_integral[0], real_integral[1:], imag_integral[1:])