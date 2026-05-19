"""
Test FftInvPdf auto-resize: issue #181.

FftInvPdf defaults to N=1024 and fits a spline on np.arange(1024).  Before the
fix, querying t > 1023 triggered UnivariateSpline extrapolation, which produced
garbage PDF values (e.g. monotonically rising instead of peaked).

After the fix, FftInvPdf detects t.max() >= N and silently resizes the FFT grid
to the next power of 2, so the spline is always queried within its fit domain.

Tests:
  1. Small-t query (t < 1024): default N=1024 path, result is a valid PDF.
  2. Large-t query (t in [455, 1393]): N auto-resizes to 2048, result matches
     the result from the timescale-scaled query (defense-in-depth check).
"""
import numpy as np
import pytest
from molass.MathUtils.FftUtils import FftInvPdf


# ---------------------------------------------------------------------------
# Minimal characteristic function: Gaussian PDF via CF  phi(w) = exp(-sigma^2*w^2/2)
# This yields a Gaussian centered at t=0 so we can compute the centroid
# analytically.
# ---------------------------------------------------------------------------

def _gaussian_cf(w, sigma=30.0):
    return np.exp(-0.5 * sigma**2 * w**2)


# CF for a Gaussian shifted by mu (using phase shift)
def _shifted_gaussian_cf(w, mu, sigma):
    return np.exp(1j * w * mu - 0.5 * sigma**2 * w**2)


fft_gauss = FftInvPdf(_gaussian_cf)
fft_shifted_gauss = FftInvPdf(_shifted_gaussian_cf)


class TestFftInvPdfAutoResize:
    """Tests for the auto-resize behaviour introduced in issue #181."""

    def test_small_t_uses_default_N(self):
        """Query within [0, 1023]: uses default N=1024, returns valid PDF."""
        t = np.linspace(0, 1000, 200)
        pdf = fft_gauss(t)
        # PDF should be non-negative
        assert np.all(pdf >= -1e-10)
        # Gaussian centered at 0 — peak should be near t=0
        assert pdf[0] == pdf.max() or np.argmax(pdf) < 5

    def test_large_t_auto_resizes_grid(self):
        """Query range [455, 1393] exceeds N=1024: FftInvPdf auto-resizes to 2048."""
        mu = 800.0   # mean of the shifted Gaussian
        sigma = 30.0

        t_large = np.arange(455, 1394, dtype=float)
        pdf_large = fft_shifted_gauss(t_large, mu, sigma)

        # Must not return NaN or Inf
        assert np.all(np.isfinite(pdf_large)), "PDF contains NaN/Inf after auto-resize"

        # PDF should be non-negative everywhere
        assert np.all(pdf_large >= -1e-8), "PDF has significant negative values"

        # Centroid should be near mu=800
        centroid = np.trapezoid(t_large * pdf_large, t_large) / np.trapezoid(pdf_large, t_large)
        assert abs(centroid - mu) < 2.0, f"Centroid {centroid:.1f} too far from mu={mu}"

    def test_large_t_matches_scaled_version(self):
        """
        Without auto-resize, callers had to scale t into [0,1023] and rescale T.
        With auto-resize, the unscaled result should match the scaled one within
        numerical tolerance.  This is the 'defense-in-depth' check.
        """
        mu = 800.0
        sigma = 30.0
        t_large = np.arange(455, 1394, dtype=float)

        # Unscaled query — FftInvPdf auto-resizes to N=2048
        pdf_unscaled = fft_shifted_gauss(t_large, mu, sigma)

        # Scaled query — manually scale into [0, 1023]
        ts = 0.6   # arbitrary timescale that keeps t_max*ts < 1024
        t_scaled = ts * t_large
        mu_scaled = ts * mu
        pdf_scaled = fft_shifted_gauss(t_scaled, mu_scaled, ts * sigma) * ts

        # Both should give the same centroid within 1 frame
        def centroid(t, p):
            return np.trapezoid(t * p, t) / np.trapezoid(p, t)

        c_unscaled = centroid(t_large, pdf_unscaled)
        c_scaled = centroid(t_large, pdf_scaled / ts)   # undo amplitude scaling for comparison

        assert abs(c_unscaled - c_scaled) < 1.0, (
            f"Centroid mismatch: unscaled={c_unscaled:.2f}, scaled={c_scaled:.2f}"
        )
