"""Fronting is allowed in the rigorous stage only where the quick EGH fit shows it (molass-library#350)."""
import numpy as np
import pytest
from types import SimpleNamespace

from molass.Rigorous.FrontingPolicy import (
    FRONTING_THRESHOLD, detect_fronting, legacy_flags, resolve_fronting, describe,
)


class _Curve:
    def __init__(self, model, sigma, tau):
        self.model = model
        self._p = [1.0, 100.0, sigma, tau]

    def get_params(self):
        return self._p


def _decomp(model, taus, sigma=20.0, source=None):
    d = SimpleNamespace(xr_ccurves=[_Curve(model, sigma, t) for t in taus], num_components=len(taus),
                        fronting_flags=None)
    if source is not None:
        d._source_decomp = source
    return d


def test_detection_uses_tau_over_sigma_not_the_sign():
    # SAMPLE3 -7.55 / 22.8 = -0.33 fronts; the noise-level taus of the other bundled components do not
    assert detect_fronting(_decomp('egh', [-7.55], sigma=22.81)) == [True]
    assert detect_fronting(_decomp('egh', [-0.0007, 0.0009, -0.004, 4e-7, 6.4])) == [False] * 5
    assert detect_fronting(_decomp('egh', [-0.2 * 20.0 * FRONTING_THRESHOLD * -1], sigma=20.0)) == [False]


def test_threshold_is_the_documented_one():
    assert FRONTING_THRESHOLD == -0.05
    assert detect_fronting(_decomp('egh', [-0.06 * 20]), threshold=FRONTING_THRESHOLD) == [True]
    assert detect_fronting(_decomp('egh', [-0.04 * 20]), threshold=FRONTING_THRESHOLD) == [False]


def test_modes():
    egh = _decomp('egh', [-7.0, 3.0])
    assert resolve_fronting(egh, 'auto') == [True, False]
    assert resolve_fronting(egh, None) == [True, False]          # nothing stored: auto
    assert resolve_fronting(egh, 'allow') == [True, True]
    assert resolve_fronting(egh, 'forbid') == [False, False]
    assert resolve_fronting(egh, [False, True]) == [False, True]
    with pytest.raises(ValueError):
        resolve_fronting(egh, [True])
    with pytest.raises(ValueError):
        resolve_fronting(egh, 'sometimes')


def test_stored_flags_win_when_no_mode_is_given():
    egh = _decomp('egh', [-7.0, 3.0])
    egh.fronting_flags = [False, False]
    assert resolve_fronting(egh, None) == [False, False]
    assert resolve_fronting(egh, 'auto') == [True, False]        # an explicit 'auto' detects again


def test_legacy_is_what_molass_did_before():
    assert legacy_flags('egh', 2) == [False, False]               # tau >= 0
    assert legacy_flags('edm', 2) == [True, True]                 # b free
    assert legacy_flags('sdm', 2) is None
    egh = _decomp('egh', [-7.0])
    assert resolve_fronting(egh, 'legacy') == [False]
    # for the upgrade to EDM the decomposition is still the EGH one: the target model decides
    assert resolve_fronting(egh, 'legacy', target_model='edm') == [True]


def test_edm_follows_its_egh_source():
    egh = _decomp('egh', [-7.0, 3.0])
    edm = _decomp('edm', [0.0, 0.0], source=egh)
    assert resolve_fronting(edm, 'auto') == [True, False]
    assert resolve_fronting(_decomp('edm', [0.0, 0.0]), 'auto') == [True, True]   # no EGH fit to judge by


def test_models_that_cannot_front_are_outside_the_policy():
    for model in ('sdm', 'lkm', 'grm'):
        assert resolve_fronting(_decomp(model, [0.0]), 'auto') is None


def test_describe():
    assert describe([False, False]) == "none"
    assert describe([True, True]) == "all"
    assert describe([False, True, False]) == "component 2"
    assert describe(None) == "not applicable"


def test_egh_rigorous_tau_bound():
    from molass_legacy.ModelParams.EghParams import EghParamsBase
    params = np.array([[0.29, 196.0, 22.8, -7.55],      # fronting
                       [0.20, 260.0, 20.0, 5.0],        # tailing
                       [0.01, 100.0, 20.0, 0.0]])       # baseline row, as in the non-advanced layout

    def tau_bounds(flags):
        obj = EghParamsBase.__new__(EghParamsBase)
        if flags is not None:
            obj.fronting_flags = flags
        b = EghParamsBase.get_xr_param_bounds(obj, params, None, None)
        return [b[4 * k + 3] for k in range(3)]

    # no flags: the former behavior, tau >= 0 for everybody (the fronting start lies outside the bounds)
    assert [lo for lo, hi in tau_bounds(None)] == [0, 0, 0]
    lo0, hi0 = tau_bounds([True, False])[0]
    assert lo0 < -7.55 and hi0 > 0                      # the start is inside
    assert tau_bounds([True, False])[1][0] == 0         # the tailing component keeps tau >= 0
    assert tau_bounds([True, False])[2][0] == 0         # and so does the baseline row
    assert all(lo < 0 for lo, hi in tau_bounds([True, True])[:2])


def test_edm_rigorous_b_bound():
    from molass_legacy.ModelParams.EdmParams import EdmParams
    obj = EdmParams(3)                                   # two components + the baseline
    abc = np.array([[0.05, -0.5, 1.0], [0.5, 0.2, 0.7]])
    b = np.array(obj.get_xr_per_comp_bounds(abc), dtype=float).reshape(2, 3, 2)[:, 1, :]
    assert b.tolist() == [[-50.0, 50.0]] * 2             # no flags: the former wide range
    obj.fronting_flags = [True, False]
    b = np.array(obj.get_xr_per_comp_bounds(abc), dtype=float).reshape(2, 3, 2)[:, 1, :]
    assert b.tolist() == [[-50.0, 50.0], [0.0, 50.0]]


def test_suggested_edm_bounds_follow_the_policy_and_the_sign():
    from molass.SEC.Models.EdmRecommend import suggest_edm_bounds_from_egh
    egh = _decomp('egh', [-7.0, 3.0])
    for cc, tR in zip(egh.xr_ccurves, (100.0, 150.0)):
        cc._p[1] = tR
    suggested = suggest_edm_bounds_from_egh(egh)
    assert suggested['b_bounds'] == [(None, None), (0.0, None)]
