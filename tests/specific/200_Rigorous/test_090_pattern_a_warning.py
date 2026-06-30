"""
Test that optimize_rigorously() emits a UserWarning when called without
trimmed_ssd on a corrected SSD (Pattern A), guiding the user towards
Pattern B (trimmed_ssd=trimmed).

See: https://github.com/biosaxs-dev/molass-library/issues/164
     https://github.com/biosaxs-dev/molass-library/issues/165 (_dry_run)
"""
import warnings
import io
import contextlib


def _make_corrected_decomp():
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


def test_corrected_copy_sets_corrected_flag():
    """corrected_copy() must set ssd.corrected = True on the returned copy."""
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD

    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()), \
         warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ssd = SSD(SAMPLE1)
        trimmed = ssd.trimmed_copy()
        corrected = trimmed.corrected_copy()

    assert getattr(corrected, 'corrected', False) is True, \
        "corrected_copy() should set ssd.corrected = True"
    assert not getattr(trimmed, 'corrected', False), \
        "trimmed_copy() should NOT set ssd.corrected = True"
    assert not getattr(ssd, 'corrected', False), \
        "raw SSD should NOT have ssd.corrected = True"


def _run_dry(decomp, trimmed_ssd, tmp_path):
    """Call optimize_rigorously(_dry_run=True) and return captured warnings.

    _dry_run fires all pre-flight checks (warnings, guards) then returns None
    without building the optimizer.  This replaces the old reload-patch hack.
    See molass-library#165 for the design rationale.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        kwargs = dict(
            analysis_folder=str(tmp_path / "test_run"),
            _dry_run=True,
        )
        if trimmed_ssd is not None:
            kwargs["trimmed_ssd"] = trimmed_ssd
        result = decomp.optimize_rigorously(**kwargs)
    assert result is None, "_dry_run=True should return None"
    return caught


def test_pattern_a_emits_user_warning(tmp_path):
    """optimize_rigorously() without trimmed_ssd on corrected data must emit UserWarning."""
    trimmed, corrected, decomp = _make_corrected_decomp()
    caught = _run_dry(decomp, trimmed_ssd=None, tmp_path=tmp_path)

    pattern_a_warnings = [w for w in caught if issubclass(w.category, UserWarning)
                          and "Pattern A" in str(w.message)]
    assert pattern_a_warnings, (
        "Expected a UserWarning mentioning 'Pattern A' when optimize_rigorously() "
        "is called without trimmed_ssd on corrected data"
    )


def test_pattern_b_no_warning(tmp_path):
    """optimize_rigorously() with trimmed_ssd must NOT emit the Pattern A warning."""
    trimmed, corrected, decomp = _make_corrected_decomp()
    caught = _run_dry(decomp, trimmed_ssd=trimmed, tmp_path=tmp_path)

    pattern_a_warnings = [w for w in caught if issubclass(w.category, UserWarning)
                          and "Pattern A" in str(w.message)]
    assert not pattern_a_warnings, (
        "No Pattern A warning should be emitted when trimmed_ssd is provided"
    )
