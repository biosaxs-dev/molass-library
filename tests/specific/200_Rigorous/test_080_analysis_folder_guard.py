"""
Test that optimize_rigorously() raises a clear ValueError when
analysis_folder is omitted (None), instead of crashing deep inside
ntpath.join with a cryptic TypeError.

See: https://github.com/biosaxs-dev/molass-library/issues/153
"""
import pytest
from unittest.mock import MagicMock


def _make_fake_decomp():
    """Return a minimal Decomposition-like object for call-site testing."""
    from molass.LowRank.Decomposition import Decomposition
    decomp = MagicMock(spec=Decomposition)
    # Wire optimize_rigorously to the real implementation so the guard fires
    decomp.optimize_rigorously = lambda **kw: Decomposition.optimize_rigorously(decomp, **kw)
    return decomp


def test_missing_analysis_folder_raises_value_error():
    """optimize_rigorously() without analysis_folder must raise ValueError immediately."""
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    import io, contextlib, warnings

    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()), \
         warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ssd = SSD(SAMPLE1)
        trimmed = ssd.trimmed_copy()
        corrected = trimmed.corrected_copy()
        decomp = corrected.quick_decomposition(num_components=2)

    with pytest.raises(ValueError, match="analysis_folder is required"):
        decomp.optimize_rigorously()  # no analysis_folder → must fail clearly
