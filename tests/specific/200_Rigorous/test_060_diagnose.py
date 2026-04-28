"""
Tests for RunInfo.diagnose() (issue #145).

diagnose() is a pure function on a breakdown dict — no disk I/O needed.
We call it via a minimal RunInfo stub by patching get_score_breakdown.
"""
import pytest
from molass.Rigorous.RunInfo import RunInfo


def _make_run_info():
    return RunInfo(ssd=None, optimizer=None, dsets=None, init_params=None)


def _diagnose_from(scores):
    """Call diagnose() with a pre-built breakdown dict."""
    ri = _make_run_info()
    breakdown = {'fv': -1.0, 'scores': scores}
    return ri.diagnose(breakdown=breakdown)


# ---------------------------------------------------------------------------
# UV failure cases (motivating case: experiment 13u)
# ---------------------------------------------------------------------------

def test_uv_lrf_failing():
    """UV_LRF_residual near zero => 'failing' diagnosis."""
    diags = _diagnose_from({
        'UV_LRF_residual': -0.04,
        'UV_2D_fitting': -0.30,
        'XR_2D_fitting': -1.61,
    })
    statuses = {d.score: d.status for d in diags}
    assert statuses.get('UV_LRF_residual') == 'failing'


def test_uv_vs_xr_ratio_poor():
    """UV_2D_fitting much worse than XR_2D_fitting => 'poor' ratio diagnosis."""
    diags = _diagnose_from({
        'UV_LRF_residual': -0.80,   # fine
        'UV_2D_fitting': -0.30,
        'XR_2D_fitting': -1.61,
    })
    statuses = {d.score: d.status for d in diags}
    assert statuses.get('UV_2D_fitting vs XR_2D_fitting') == 'poor'


def test_uv_vs_xr_ratio_fair():
    """Moderate UV/XR ratio (0.33-0.67) => 'fair'."""
    diags = _diagnose_from({
        'UV_LRF_residual': -0.80,
        'UV_2D_fitting': -0.80,   # ratio = 0.80/1.61 = 0.50 -> fair
        'XR_2D_fitting': -1.61,
    })
    statuses = {d.score: d.status for d in diags}
    assert statuses.get('UV_2D_fitting vs XR_2D_fitting') == 'fair'


def test_suggestion_references_get_current_curves():
    """Failing UV diagnosis should suggest get_current_curves()."""
    diags = _diagnose_from({
        'UV_LRF_residual': -0.04,
        'UV_2D_fitting': -0.30,
        'XR_2D_fitting': -1.61,
    })
    uv_lrf_diag = next(d for d in diags if d.score == 'UV_LRF_residual')
    assert uv_lrf_diag.suggestion is not None
    assert 'get_current_curves' in uv_lrf_diag.suggestion


# ---------------------------------------------------------------------------
# Guinier and penalty cases
# ---------------------------------------------------------------------------

def test_guinier_poor():
    """Guinier_deviation near zero => 'poor'."""
    diags = _diagnose_from({'Guinier_deviation': -0.1})
    statuses = {d.score: d.status for d in diags}
    assert statuses.get('Guinier_deviation') == 'poor'


def test_penalty_flagged():
    """A non-zero penalty > 0.1 should appear in the diagnosis."""
    diags = _diagnose_from({'negative_penalty': 0.5})
    statuses = {d.score: d.status for d in diags}
    assert statuses.get('negative_penalty') == 'poor'


# ---------------------------------------------------------------------------
# All-good case
# ---------------------------------------------------------------------------

def test_all_good_returns_single_good_entry():
    """When all scores are healthy, diagnose() returns a single 'good' entry."""
    diags = _diagnose_from({
        'UV_LRF_residual': -1.2,
        'UV_2D_fitting': -1.3,
        'XR_2D_fitting': -1.5,
        'Guinier_deviation': -1.1,
        'SEC_conformance': -0.8,
        'mapping_penalty': 0.0,
        'negative_penalty': 0.0,
    })
    assert len(diags) == 1
    assert diags[0].status == 'good'


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

def test_returns_named_tuples():
    """Each item must be a namedtuple with expected fields."""
    diags = _diagnose_from({'UV_LRF_residual': -0.04})
    for d in diags:
        assert hasattr(d, 'score')
        assert hasattr(d, 'status')
        assert hasattr(d, 'reason')
        assert hasattr(d, 'suggestion')
        assert d.status in ('good', 'fair', 'poor', 'failing')
