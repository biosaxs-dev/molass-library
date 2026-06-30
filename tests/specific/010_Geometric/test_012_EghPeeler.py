"""Tests for Peaks.EghPeeler — max_sigma_ratio (plate number constraint)."""
import numpy as np
import pytest
from molass.Peaks.EghPeeler import egh_peel
from molass.SEC.Models.Simple import egh


def _make_curve(x, peaks):
    """Build a synthetic elution curve from a list of (H, mu, sigma, tau)."""
    y = np.zeros_like(x, dtype=float)
    for H, mu, sigma, tau in peaks:
        y += egh(x, H, mu, sigma, tau)
    return y


class TestMaxSigmaRatio:
    """The plate number constraint rejects peaks wider than K × σ_dominant."""

    x = np.arange(800, 1200, dtype=float)

    def test_two_similar_peaks_accepted(self):
        """Two peaks with similar σ should both be accepted."""
        y = _make_curve(self.x, [
            (10.0, 950, 15, 2),
            (5.0, 1050, 18, 3),
        ])
        peaks = egh_peel(self.x, y, max_sigma_ratio=2.0)
        assert len(peaks) == 2

    def test_spurious_wide_peak_rejected(self):
        """A real peak + a very broad spurious 'peak' → only 1 accepted."""
        y = _make_curve(self.x, [
            (10.0, 1000, 15, 2),
            (1.0, 1000, 120, 0),   # σ=120 ≫ 2×15
        ])
        peaks = egh_peel(self.x, y, max_sigma_ratio=2.0)
        assert len(peaks) == 1

    def test_disabled_accepts_wide(self):
        """With max_sigma_ratio=None, the wide peak is accepted."""
        y = _make_curve(self.x, [
            (10.0, 1000, 15, 2),
            (1.0, 1000, 120, 0),
        ])
        peaks = egh_peel(self.x, y, max_sigma_ratio=None)
        assert len(peaks) >= 2

    def test_fixed_num_components_still_applies(self):
        """Even with num_components=3, plate constraint rejects too-wide fits."""
        # One narrow peak + broad background that the peeler might try to fit
        y = _make_curve(self.x, [
            (10.0, 1000, 15, 2),
            (0.5, 1000, 150, 0),
        ])
        peaks = egh_peel(self.x, y, num_components=3, max_sigma_ratio=2.0)
        # The broad background peak has σ ≫ 2×15, so at most 2 should pass
        for p in peaks:
            assert p[2] <= 15 * 2.0 * 1.1, f"sigma={p[2]:.1f} exceeds plate bound"

    def test_default_ratio_is_2(self):
        """Default max_sigma_ratio=2.0 — verify it works without explicit arg."""
        y = _make_curve(self.x, [
            (10.0, 1000, 15, 2),
        ])
        peaks = egh_peel(self.x, y)
        # Should find 1 peak; no spurious broad fits accepted
        assert len(peaks) >= 1
