"""Regression tests for compute_proportional_boundaries robustness (molass-library#307)."""
import numpy as np
import pytest
from molass.Decompose.Proportional import compute_proportional_boundaries


def test_boundaries_unchanged_for_well_behaved_curve():
    x = np.arange(200, dtype=float)
    y = np.exp(-0.5 * ((x - 100) / 15) ** 2)
    b = compute_proportional_boundaries(x, y, [1, 1])
    assert b == pytest.approx([100.0], abs=1.0)


def test_tiny_positive_tail_values_do_not_break_the_spline():
    x = np.arange(300, dtype=float)
    y = np.exp(-0.5 * ((x - 100) / 15) ** 2)
    y[200:] = 1e-30            # lost to rounding in the cumulative sum
    b = compute_proportional_boundaries(x, y, [1, 1])
    assert b == pytest.approx([100.0], abs=1.0)


def test_too_few_usable_points_gives_clear_error():
    x = np.arange(10, dtype=float)
    y = np.zeros(10)
    y[3] = 1.0
    with pytest.raises(ValueError, match="Cannot compute proportional boundaries"):
        compute_proportional_boundaries(x, y, [1, 1])
