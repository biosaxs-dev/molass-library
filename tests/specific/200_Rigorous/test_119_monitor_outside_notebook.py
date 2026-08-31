"""
Test that optimize_rigorously() degrades monitor=True (the default) to
monitor=False with a UserWarning when run outside a Jupyter/IPython notebook,
instead of crashing (Tcl_AsyncDelete: async handler deleted by the wrong
thread) when the MplMonitor dashboard's ipywidgets/matplotlib calls run from
a background thread with no notebook display support.

Found running a plain validation script (no notebook) for
https://github.com/biosaxs-dev/molass-library/issues/259.
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


def test_monitor_true_outside_notebook_warns_and_degrades(tmp_path):
    """monitor=True (default) outside a notebook must warn, not crash."""
    trimmed, corrected, decomp = _make_decomp()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = decomp.optimize_rigorously(
            analysis_folder=str(tmp_path / "test_run"),
            _dry_run=True,
        )

    assert result is None, "_dry_run=True should return None"
    monitor_warnings = [
        w for w in caught
        if issubclass(w.category, UserWarning) and "monitor=True" in str(w.message)
    ]
    assert monitor_warnings, (
        "Expected a UserWarning about monitor=True having no effect outside a notebook. "
        f"Got: {[str(w.message) for w in caught]}"
    )


def test_monitor_false_no_warning(tmp_path):
    """monitor=False must NOT emit the monitor-degrade warning."""
    trimmed, corrected, decomp = _make_decomp()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = decomp.optimize_rigorously(
            analysis_folder=str(tmp_path / "test_run"),
            monitor=False,
            _dry_run=True,
        )

    assert result is None, "_dry_run=True should return None"
    monitor_warnings = [
        w for w in caught
        if issubclass(w.category, UserWarning) and "monitor=True" in str(w.message)
    ]
    assert not monitor_warnings, (
        "No monitor-degrade warning should be emitted when monitor=False. "
        f"Got: {[str(w.message) for w in caught]}"
    )
