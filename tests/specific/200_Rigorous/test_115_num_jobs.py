"""
Test the num_jobs successive-jobs loop parameter added to optimize_rigorously().

num_jobs > 1 runs that many full rounds, each reseeding init_params from the
best params found across all previous rounds (clear_jobs=(round == 0)), the
same mechanism validated on real BH/DE data in
molass-researcher/experiments/36_bh_cutomize_trial. These tests only cover
the fast, pre-flight-only guard paths (via _dry_run=True, same convention as
test_090_pattern_a_warning.py / test_100_cma_async_fallback.py) -- the actual
multi-round reseed behavior is exercised by that real-data experiment, not a
fast unit test.

See: https://github.com/biosaxs-dev/molass-library/issues/257 (related, max_trials)
"""
import warnings
import io
import contextlib

import pytest


def _make_decomp():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD

    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()), \
         warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ssd = SSD(SAMPLE1)
        trimmed = ssd.trimmed_copy()
        corrected = trimmed.corrected_copy()
        decomp = corrected.quick_decomposition(num_components=2)
    return trimmed, corrected, decomp


def test_num_jobs_with_async_true_raises(tmp_path):
    """num_jobs > 1 with async_=True (the default) must raise ValueError."""
    trimmed, corrected, decomp = _make_decomp()

    with pytest.raises(ValueError, match="num_jobs > 1 requires async_=False"):
        decomp.optimize_rigorously(
            analysis_folder=str(tmp_path / "test_run"),
            num_jobs=3,
        )


def test_num_jobs_with_max_trials_warns(tmp_path):
    """num_jobs > 1 together with max_trials must emit a UserWarning (both would stack)."""
    trimmed, corrected, decomp = _make_decomp()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = decomp.optimize_rigorously(
            analysis_folder=str(tmp_path / "test_run"),
            num_jobs=3,
            async_=False,
            max_trials=5,
            _dry_run=True,
        )

    assert result is None, "_dry_run=True should return None"
    stack_warnings = [
        w for w in caught
        if issubclass(w.category, UserWarning) and "max_trials" in str(w.message)
    ]
    assert stack_warnings, (
        "Expected a UserWarning about num_jobs and max_trials both being requested. "
        f"Got: {[str(w.message) for w in caught]}"
    )


def test_num_jobs_default_no_max_trials_warning(tmp_path):
    """num_jobs=1 (default) with max_trials set must NOT emit the stacking warning."""
    trimmed, corrected, decomp = _make_decomp()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = decomp.optimize_rigorously(
            analysis_folder=str(tmp_path / "test_run"),
            async_=False,
            max_trials=5,
            _dry_run=True,
        )

    assert result is None, "_dry_run=True should return None"
    stack_warnings = [
        w for w in caught
        if issubclass(w.category, UserWarning) and "max_trials" in str(w.message)
    ]
    assert not stack_warnings, (
        "No num_jobs/max_trials warning should be emitted when num_jobs=1 (default). "
        f"Got: {[str(w.message) for w in caught]}"
    )


def test_num_jobs_dry_run_returns_none(tmp_path):
    """num_jobs > 1 with _dry_run=True must return None, not crash on run_info.wait().

    Regression test: the loop originally called run_info.wait(timeout=0)
    unconditionally, but make_rigorous_decomposition_impl(_dry_run=True)
    returns None -- crashing with AttributeError before this fix.
    """
    trimmed, corrected, decomp = _make_decomp()

    result = decomp.optimize_rigorously(
        analysis_folder=str(tmp_path / "test_run"),
        num_jobs=3,
        async_=False,
        _dry_run=True,
    )
    assert result is None


def test_num_jobs_single_matches_old_default(tmp_path):
    """num_jobs=1 (default) must not change existing single-job behavior/validation."""
    trimmed, corrected, decomp = _make_decomp()

    # async_=True is the historical default and must remain valid when num_jobs=1.
    result = decomp.optimize_rigorously(
        analysis_folder=str(tmp_path / "test_run"),
        _dry_run=True,
    )
    assert result is None
