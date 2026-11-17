"""upgrade(model, match_curves=True): fit the new components to the source component curves (molass-library#395)."""
import numpy as np
import pytest

from molass.SEC.Models.GrmComponentCurve import GrmComponentCurve
from molass.SEC.Models.LkmComponentCurve import LkmComponentCurve
from molass.SEC.Models.MatchCurves import match_ccurves, check_model

X = np.arange(0.0, 400.0)


def _lkm(Pe, t0, params):
    return [LkmComponentCurve(X, Pe, t0, k_MT=k, R=R, c_inj=c, rg=30.0) for k, R, c in params]


def _grm(Pe, t0, params, R_p=0.0035, D_eff=1e3, F=1.5):
    return [GrmComponentCurve(X, Pe, t0, R_p, D_eff, (R - 1.0) / F, F, k_ext=k, R=R, c_inj=c, rg=30.0)
            for k, R, c in params]


def _rms(a, b):
    return float(np.sqrt(np.mean([(p.get_y(X) - q.get_y(X)) ** 2 for p, q in zip(a, b)])))


@pytest.mark.parametrize("model, make, truth, start", [
    ("LKM", _lkm, (300.0, 40.0, [(0.5, 3.0, 40.0), (0.4, 4.5, 60.0)]),
                  (200.0, 42.0, [(0.8, 3.2, 30.0), (0.7, 4.2, 70.0)])),
    ("GRM", _grm, (300.0, 40.0, [(0.01, 3.0, 40.0), (0.008, 4.5, 60.0)]),
                  (150.0, 40.0, [(0.02, 3.0, 30.0), (0.016, 4.5, 70.0)])),
])
def test_perturbed_curves_are_pulled_back_to_the_source(model, make, truth, start):
    # as after upgrade(): the peak positions are the source's, the shapes and scales are not
    source = make(*truth)
    perturbed = make(*start)
    fitted, info = match_ccurves(model, source, perturbed, X)
    assert info["improved"] and info["error"] < 0.2 * info["start_error"]
    assert _rms(fitted, source) < 0.2 * _rms(perturbed, source)
    assert [type(c) for c in fitted] == [type(c) for c in perturbed]
    assert all(c.rg == 30.0 for c in fitted)                 # what is not fitted is kept


def test_a_fit_that_does_not_improve_returns_the_start_curves():
    source = _lkm(300.0, 40.0, [(0.5, 3.0, 40.0)])
    fitted, info = match_ccurves("LKM", source, source, X)   # already exact: nothing to gain
    assert not info["improved"] and fitted[0] is source[0]


def test_other_models_are_refused_before_any_work():
    for model in ("SDM", "EDM", "egh"):
        with pytest.raises(NotImplementedError, match="GRM, LKM"):
            check_model(model)
    check_model("grm")


def test_upgrade_refuses_unsupported_models_and_keeps_the_default_off():
    from types import SimpleNamespace
    from molass.LowRank.Decomposition import Decomposition
    with pytest.raises(NotImplementedError):
        Decomposition.upgrade(SimpleNamespace(), "SDM", match_curves=True)
    assert Decomposition.upgrade.__kwdefaults__["match_curves"] is False


def test_the_number_of_curves_must_agree():
    with pytest.raises(ValueError):
        match_ccurves("LKM", _lkm(300.0, 40.0, [(0.5, 3.0, 40.0)]), _lkm(300.0, 40.0, [(0.5, 3.0, 40.0)] * 2), X)
