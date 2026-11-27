"""Which points the Rg comes from (molass-library#419): the repr / describe() of RgEstimator and molass.Guinier.rg_conventions. Simulated profile; no local data."""
import numpy as np

from molass.Guinier import rg_conventions
from molass.Guinier.RgConventions import fixed_guinier_fit
from molass.Guinier.RgEstimator import RgEstimator, LOW_SCORE_WARN
from molass.Testing import sphere_form_factor

RG = 33.0


def _profile(seed=0):
    q = np.linspace(0.0075, 0.3, 300)
    I = 0.33 * sphere_form_factor(q, RG)
    e = 0.002 * np.ones_like(q)
    return q, I + e * np.random.default_rng(seed).standard_normal(q.size), e


def test_repr_and_describe_say_which_points_were_used():
    q, I, e = _profile()
    est = RgEstimator(np.array([q, I, e]).T)
    iv = est._interval()
    assert iv['min_q'] is not None and iv['n_points'] >= 5 and iv['qrg_max'] == est.max_q * est.Rg
    text = repr(est)
    assert text.startswith("RgEstimator(Rg=") and "points" in text and "source='legacy'" in text and "q*Rg max" in text
    d = est.describe()
    assert f"{iv['n_points']} points" in d and "rg_source = 'legacy'" in d
    assert est.low_score is False and "low fit score" not in d            # a clean profile has a high score
    est.score = LOW_SCORE_WARN - 0.1                                      # a low score is named in the report
    assert est.low_score and "(low)" in repr(est) and "rg_conventions" in est.describe()


def test_rg_conventions_gives_both_intervals_and_the_spread():
    q, I, e = _profile()
    conv = rg_conventions(q, I, e)
    assert len(conv) == 2
    for v in conv.values():
        assert abs(v['Rg'] - RG) / RG < 0.03 and v['n_points'] >= 5 and v['min_q'] < v['max_q']
    assert conv.spread < 0.05 * RG
    text = repr(conv)
    assert "adaptive (RgEstimator)" in text and "from lowest q (q*Rg < 1.3)" in text and "spread" in text
    # the fixed fit starts at the lowest q
    assert list(conv.values())[1]['min_q'] == q[0]


def test_fixed_guinier_fit_fails_with_nan_not_an_exception():
    q = np.linspace(0.01, 0.1, 40)
    out = fixed_guinier_fit(q, np.exp(+q ** 2 * 100))                   # a rising profile has no Guinier region
    assert np.isnan(out['Rg']) and out['n_points'] >= 0
