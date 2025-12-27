"""
    MathUtils/FftUtils.py
"""
import numpy as np
from scipy.interpolate import UnivariateSpline

def compute_standard_wCD(N):
    # extracted from molass_legacy/CharFunc/cf2DistFFT.py
    xMin = 0
    xMax = N
    xRange = xMax - xMin
    dt  = 2*np.pi / xRange
    # dt = 1/xRange
    k   = np.arange(N, dtype=complex)     # np.complex is deprecated, or use np.complex128
    w   = (k - N/2 + 0.5) * dt
    A   = xMin
    B   = xMax
    # dx  = (B-A)/N
    c   = (-1)**(A*(N-1)/(B-A))/(B-A)
    # print("A, B, N, dx, c=", A, B, N, dx, c)
    C = c * (-1)**((1-1/N)*k)
    D = (-1)**(-2*(A/(B-A))*k)     # k must be complex, see https://stackoverflow.com/questions/45384602/numpy-runtimewarning-invalid-value-encountered-in-power
    return w, C, D

class FftInvPdf:
    def __init__(self, cf):
        self.cf = cf
        self.N = N = 1024
        self.w, self.C, self.D = compute_standard_wCD(N)

    def __call__(self, t, *params):
        N = self.N
        cft = self.cf(self.w[N//2:], *params)
        cft = np.concatenate([cft[::-1].conj(), cft])
        pdfFFT = np.max([np.zeros(N), (self.C*np.fft.fft(self.D*cft)).real], axis=0)
        spline = UnivariateSpline(np.arange(N), pdfFFT, s=0)
        return spline(t)