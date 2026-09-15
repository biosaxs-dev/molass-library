"""
Test: decompose_proportionally() should not collapse a component to (near) zero
area when a requested proportional slice is dominated by background noise rather
than real peak signal.

Found via a real sample (Plk1, 2026-07-28) that has only one true species: forcing
num_components=3, proportions=[1,1,1] produced a component with H=0 (0% of the
final area), which then broke downstream Guinier analysis with a cryptic error far
removed from the actual cause. Root cause: the per-slice moment/initial-EGH-fit was
computed over the whole (mostly-background) slice range instead of its signal-bearing
sub-region, anchoring the joint optimizer's bounds away from the real peak entirely.
"""
import numpy as np
import pytest
from molass.SEC.Models.Simple import egh
from molass.Decompose.Proportional import decompose_proportionally


class _FakeICurve:
    """Minimal ICurve stand-in -- decompose_proportionally only needs get_xy()."""
    def __init__(self, x, y):
        self._x = x
        self._y = y

    def get_xy(self):
        return self._x, self._y


@pytest.fixture(scope="module")
def single_peak_with_noise():
    """One real EGH peak plus low-level background noise, mimicking a sample with
    only one true species spread over a much wider trimmed frame range."""
    rng = np.random.default_rng(0)
    x = np.arange(264, 1598)
    y = egh(x, 0.052, 929, 13.5, 30) + rng.normal(0, 0.0008, size=x.shape)
    return x, y


def test_forced_3components_on_1peak_no_degenerate_component(single_peak_with_noise):
    """Requesting 3 equal-proportion components on single-peak data must not
    collapse any component to (near) zero area."""
    x, y = single_peak_with_noise
    result = decompose_proportionally(_FakeICurve(x, y), [1, 1, 1])

    params = result.x.reshape(3, 4)
    areas = np.array([np.sum(egh(x, *p)) for p in params])
    total = areas.sum()

    assert total > 0
    assert (areas / total > 0.15).all(), f"a component collapsed to near-zero: areas={areas}"
