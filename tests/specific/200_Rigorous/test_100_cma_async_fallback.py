"""
Test that optimize_rigorously() falls back to async_=False and emits a
UserWarning when called with method='CMA', in_process=True, async_=True.

This guard prevents STATUS_ACCESS_VIOLATION kernel crashes caused by
IPython's asyncio event loop running concurrently with the optimizer's
NumPy BLAS daemon thread on Windows / Python 3.14+.

See: https://github.com/biosaxs-dev/molass-library/issues/193
     molass-researcher experiments/21_rigorous_solvers/21c_cma_inprocess_repro.ipynb
"""
import warnings
import io
import contextlib


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


def test_cma_inprocess_async_emits_warning(tmp_path):
    """optimize_rigorously(method='CMA', in_process=True, async_=True) must emit UserWarning."""
    trimmed, corrected, decomp = _make_decomp()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = decomp.optimize_rigorously(
            analysis_folder=str(tmp_path / "test_run"),
            method="CMA",
            in_process=True,
            async_=True,
            _dry_run=True,
        )

    assert result is None, "_dry_run=True should return None"
    cma_warnings = [
        w for w in caught
        if issubclass(w.category, UserWarning)
        and "CMA" in str(w.message)
        and "async_=False" in str(w.message)
    ]
    assert cma_warnings, (
        "Expected a UserWarning mentioning 'CMA' and 'async_=False' when "
        "optimize_rigorously(method='CMA', in_process=True, async_=True) is called. "
        f"Got: {[str(w.message) for w in caught]}"
    )


def test_cma_async_false_no_warning(tmp_path):
    """optimize_rigorously(method='CMA', async_=False) must NOT emit the CMA async warning."""
    trimmed, corrected, decomp = _make_decomp()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = decomp.optimize_rigorously(
            analysis_folder=str(tmp_path / "test_run"),
            method="CMA",
            in_process=True,
            async_=False,
            _dry_run=True,
        )

    assert result is None, "_dry_run=True should return None"
    cma_warnings = [
        w for w in caught
        if issubclass(w.category, UserWarning)
        and "CMA" in str(w.message)
        and "async_=False" in str(w.message)
    ]
    assert not cma_warnings, (
        "No CMA async warning should be emitted when async_=False is already set. "
        f"Got: {[str(w.message) for w in caught]}"
    )


def test_bh_inprocess_async_no_warning(tmp_path):
    """optimize_rigorously(method='BH', in_process=True, async_=True) must NOT emit the CMA warning."""
    trimmed, corrected, decomp = _make_decomp()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = decomp.optimize_rigorously(
            analysis_folder=str(tmp_path / "test_run"),
            method="BH",
            in_process=True,
            async_=True,
            _dry_run=True,
        )

    assert result is None, "_dry_run=True should return None"
    cma_warnings = [
        w for w in caught
        if issubclass(w.category, UserWarning)
        and "CMA" in str(w.message)
        and "async_=False" in str(w.message)
    ]
    assert not cma_warnings, (
        "No CMA async warning should be emitted for method='BH'. "
        f"Got: {[str(w.message) for w in caught]}"
    )
