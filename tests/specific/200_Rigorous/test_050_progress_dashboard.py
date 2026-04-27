"""
Tests for the progress='dashboard' kwarg added in Phase 4 (molass-library#139).

These tests verify the validation guards only — the live MplMonitor dashboard
cannot be meaningfully tested in a headless environment.
"""
import pytest


def test_unknown_progress_value_raises():
    """progress='unknown' must raise ValueError with informative message."""
    from molass.Rigorous.RigorousImplement import make_rigorous_decomposition_impl

    with pytest.raises(ValueError, match="Unknown progress="):
        make_rigorous_decomposition_impl(
            decomposition=None, rgcurve=None,
            in_process=True, async_=True,
            progress='unknown',
        )


def test_dashboard_without_in_process_raises():
    """progress='dashboard' requires in_process=True."""
    from molass.Rigorous.RigorousImplement import make_rigorous_decomposition_impl

    with pytest.raises(ValueError, match="requires in_process=True and async_=True"):
        make_rigorous_decomposition_impl(
            decomposition=None, rgcurve=None,
            in_process=False, async_=True,
            progress='dashboard',
        )


def test_dashboard_without_async_raises():
    """progress='dashboard' requires async_=True."""
    from molass.Rigorous.RigorousImplement import make_rigorous_decomposition_impl

    with pytest.raises(ValueError, match="requires in_process=True and async_=True"):
        make_rigorous_decomposition_impl(
            decomposition=None, rgcurve=None,
            in_process=True, async_=False,
            progress='dashboard',
        )


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
    """Decomposition.optimize_rigorously accepts progress= and forwards it.

    Validation fires before any data access, so passing progress='bad'
    raises ValueError even when decomposition/rgcurve are None.
    """
    from molass.LowRank.Decomposition import Decomposition

    decomp = object.__new__(Decomposition)
    with pytest.raises(ValueError, match="Unknown progress="):
        decomp.optimize_rigorously(progress='bad', in_process=True, async_=True)
