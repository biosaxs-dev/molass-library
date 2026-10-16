"""
Test the public dry_run option of optimize_rigorously() (molass-library#308).
_dry_run is kept as a backward-compatible alias.
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
    return trimmed, decomp


@pytest.mark.parametrize("flag", ["dry_run", "_dry_run"])
def test_dry_run_returns_none_and_creates_nothing(tmp_path, flag):
    trimmed, decomp = _make_decomp()
    folder = tmp_path / "test_run"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = decomp.optimize_rigorously(analysis_folder=str(folder), trimmed_ssd=trimmed,
                                            monitor=False, **{flag: True})
    assert result is None
    assert not folder.exists()


def test_dry_run_is_not_forwarded_as_solver_kwarg(tmp_path):
    """dry_run must be an explicit option, not swallowed by the **kwargs solver catch-all."""
    trimmed, decomp = _make_decomp()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = decomp.optimize_rigorously(analysis_folder=str(tmp_path / "r"), trimmed_ssd=trimmed,
                                            monitor=False, dry_run=True)
    assert result is None
    assert not [w for w in caught if "dry_run" in str(w.message)]
