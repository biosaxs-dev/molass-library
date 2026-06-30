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
    """
    Numerically invert a characteristic function (CF) to obtain a PDF via FFT.

    The FFT operates on a fixed integer grid ``[0, N]`` (default ``N=1024``).
    The input time array passed to ``__call__`` must therefore be **pre-scaled**
    so that the peak of the PDF falls within roughly ``[10, 100]`` on that grid.

    Typical usage in a model wrapper::

        _impl = FftInvPdf(my_cf)

        def my_pdf(x, ..., timescale=None):
            # Rule of thumb: map the peak position t_peak to ~80 on the grid.
            if timescale is None:
                timescale = 80.0 / t_peak
            ts = timescale
            return ts * _impl(ts * x, ...)   # inverse-scale the amplitude

    The caller is responsible for both the forward scaling (``ts * x``) and the
    inverse-amplitude scaling (``ts * result``) so that the returned values form
    a proper PDF integrating to 1 over the original (unscaled) time axis.
    """
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
        """
        Evaluate the PDF at the pre-scaled time points ``t``.

        Parameters
        ----------
        t : array-like
            Sorted, non-negative, **pre-scaled** time values.  Must satisfy
            ``t[-1] < N`` for best accuracy (auto-resize handles larger values
            at the cost of coarser resolution).  See class docstring for the
            recommended scaling convention.
        *params
            Additional parameters forwarded verbatim to the characteristic
            function ``cf(w, *params)``.

        Returns
        -------
        ndarray
            PDF values at ``t``.  Integrates to 1 on the **pre-scaled** axis;
            divide by ``timescale`` (or equivalently multiply by ``1/timescale``)
            to obtain the PDF on the original time axis — or let the wrapper
            handle this via ``ts * __call__(ts * x, ...)``.
        """
        N = self.default_N
        t_max = t[-1]  # t is a sorted, pre-scaled time array
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