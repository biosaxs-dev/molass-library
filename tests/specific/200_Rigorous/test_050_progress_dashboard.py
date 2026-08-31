"""Tests for the progress kwarg in optimize_rigorously.

molass-library#139: progress='dashboard' kwarg added in Phase 4.
molass-library#159: progress is now deprecated/internal; invalid combinations
auto-degrade silently instead of raising.  Tests updated accordingly.

The live MplMonitor dashboard cannot be meaningfully tested in a headless
environment.
"""
import pytest


def test_unknown_progress_value_raises():
    """progress='unknown' is silently ignored (deprecated since #159).

    The function must get past the progress guard and fail later on
    decomposition=None, not at the progress check.
    """
    from molass.Rigorous.RigorousImplement import make_rigorous_decomposition_impl

    with pytest.raises(Exception) as exc_info:
        make_rigorous_decomposition_impl(
            decomposition=None, rgcurve=None,
            in_process=True, async_=True,
            progress='unknown',
        )
    assert "progress" not in str(exc_info.value).lower()


def test_dashboard_without_in_process_degrades_silently():
    """progress='dashboard' with in_process=False auto-degrades; no ValueError.

    molass-library#159: users should not need to pass progress=None explicitly.
    The function must get past the progress guard (failing later on
    decomposition=None), not at the progress check.
    """
    from molass.Rigorous.RigorousImplement import make_rigorous_decomposition_impl

    with pytest.raises(Exception) as exc_info:
        make_rigorous_decomposition_impl(
            decomposition=None, rgcurve=None,
            in_process=False, async_=True,
            progress='dashboard',
        )
    assert "progress" not in str(exc_info.value).lower()


def test_dashboard_without_async_degrades_silently():
    """progress='dashboard' with async_=False auto-degrades; no ValueError.

    molass-library#159: users should not need to pass progress=None explicitly.
    """
    from molass.Rigorous.RigorousImplement import make_rigorous_decomposition_impl

    with pytest.raises(Exception) as exc_info:
        make_rigorous_decomposition_impl(
            decomposition=None, rgcurve=None,
            in_process=True, async_=False,
            progress='dashboard',
        )
    assert "progress" not in str(exc_info.value).lower()


def test_none_progress_passes_validation():
    """progress=None (default) must pass the guard without error.

    We verify this by confirming the function gets past the guard and fails
    later (on the decomposition=None), not at the progress check.
    """
    from molass.Rigorous.RigorousImplement import make_rigorous_decomposition_impl

    with pytest.raises(Exception) as exc_info:
        make_rigorous_decomposition_impl(
            decomposition=None, rgcurve=None,
            in_process=True, async_=False,
            progress=None,
        )
    # Must NOT be the progress ValueError
    assert "progress" not in str(exc_info.value).lower()


def test_decomposition_progress_kwarg_forwarded():
    """Decomposition.optimize_rigorously silently ignores unknown progress= values.

    progress is deprecated (#159); the function should proceed past the progress
    check and fail later (on the missing ssd), not at the progress check.
    """
    from molass.LowRank.Decomposition import Decomposition

    decomp = object.__new__(Decomposition)
    with pytest.raises(Exception) as exc_info:
        decomp.optimize_rigorously(progress='bad', in_process=True, async_=True,
                                   analysis_folder='dummy')
    assert "progress" not in str(exc_info.value).lower()
