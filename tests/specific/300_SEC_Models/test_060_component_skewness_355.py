"""Component skewness for every elution model (molass-library#355): third standardized moment of the sampled
elution curve, negative = fronting."""
import numpy as np
import pytest

from molass.Stats.Moment import compute_skewness
from molass.LowRank.ComponentCurve import ComponentCurve
from molass.Rigorous.AnalysisFolder import AnalysisInfo


def test_compute_skewness_of_known_shapes():
    x = np.linspace(-10, 10, 4001)
    gauss = np.exp(-x**2 / 2)
    assert compute_skewness(x, gauss) == pytest.approx(0.0, abs=1e-9)
    t = np.linspace(0, 60, 60001)
    expo = np.exp(-t)                                       # exponential: skewness 2
    assert compute_skewness(t, expo) == pytest.approx(2.0, abs=2e-2)
    assert compute_skewness(-t, expo) == pytest.approx(-2.0, abs=2e-2)      # mirrored: fronting


def test_compute_skewness_does_not_depend_on_the_scale():
    t = np.linspace(0, 60, 6001)
    y = np.exp(-t) * (1 + 0.3 * t)
    assert compute_skewness(t, 7.5 * y) == pytest.approx(compute_skewness(t, y))


@pytest.mark.parametrize("y", [np.zeros(10), -np.ones(10), np.array([0, 0, 1, 0, 0, 0, 0, 0, 0, 0.0])])
def test_compute_skewness_is_nan_without_area_or_spread(y):
    assert np.isnan(compute_skewness(np.arange(10.0), y))


def test_component_curve_skewness_follows_the_sign_of_tau():
    x = np.arange(0, 300, 1.0)
    tailing = ComponentCurve(x, [1.0, 100.0, 8.0, 10.0]).skewness()
    fronting = ComponentCurve(x, [1.0, 100.0, 8.0, -10.0]).skewness()
    symmetric = ComponentCurve(x, [1.0, 100.0, 8.0, 0.0]).skewness()
    assert tailing > 0.3 and fronting < -0.3 and abs(symmetric) < 1e-6


class _FakeResult:
    fv, sv = -1.5, 80.0

    def get_skewnesses(self):
        return [0.25, -0.5]


def _info(result):
    return AnalysisInfo("analysis-x", result, "001", None, None, None,
                        dict(model='egh', num_components=2, method='bh'), [], None)


def test_analysis_summary_shows_component_skewness():
    info = _info(_FakeResult())
    assert info.component_skewness == [0.25, -0.5]
    assert "component skewness (negative = fronting): 0.25, -0.50" in info.summary()


def test_analysis_summary_without_a_result_has_no_skewness():
    info = _info(None)
    assert info.component_skewness is None
    assert "skewness" not in info.summary()


def test_analysis_summary_survives_a_result_that_cannot_give_skewness():
    class _NoSkew:
        fv, sv = -1.5, 80.0

    class _Broken(_NoSkew):
        def get_skewnesses(self):
            raise RuntimeError("no curves")

    for result in (_NoSkew(), _Broken()):
        info = _info(result)
        assert info.component_skewness is None
        text = info.summary()
        assert "result: job 001, fv=-1.5000" in text and "skewness" not in text


def test_decomposition_and_component_report_the_skewness():
    import molass_data
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(molass_data.SAMPLE3).trimmed_copy().corrected_copy()
    decomp = ssd.quick_decomposition(num_components=1)
    skews = decomp.get_skewnesses()
    assert len(skews) == 1 and skews[0] < -0.2          # SAMPLE3 has a fronting peak (EGH tau < 0)
    assert decomp.get_xr_components()[0].skewness() == pytest.approx(skews[0])
