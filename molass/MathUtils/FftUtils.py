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
        self.default_N = 1024
        self.w, self.C, self.D = compute_standard_wCD(self.default_N)
        # Cache for the resized grid (lazily populated on first large-t call).
        # t is constant across all calls for a given dataset, so N_large is
        # computed only once regardless of how many PDF evaluations are made.
        self._large_N = None
        self._large_w = self._large_C = self._large_D = None

    def __call__(self, t, *params):
        N = self.default_N
        t_max = t[-1]  # t is always a sorted frame array (x - t0)
        if t_max >= N:
            # Auto-resize to the next power of 2 that covers the query range.
            # Without this, UnivariateSpline would extrapolate outside [0, N-1],
            # producing garbage PDF values (e.g. for unscaled lognormal models
            # with raw frame values ~[455, 1393]).  See issue #181.
            N = int(2 ** np.ceil(np.log2(t_max + 2)))
            if N != self._large_N:
                self._large_w, self._large_C, self._large_D = compute_standard_wCD(N)
                self._large_N = N
            w, C, D = self._large_w, self._large_C, self._large_D
        else:
            w, C, D = self.w, self.C, self.D

        cft = self.cf(w[N//2:], *params)
        cft = np.concatenate([cft[::-1].conj(), cft])
        pdfFFT = np.max([np.zeros(N), (C*np.fft.fft(D*cft)).real], axis=0)
        spline = UnivariateSpline(np.arange(N), pdfFFT, s=0)
        return spline(t)