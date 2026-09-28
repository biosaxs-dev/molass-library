"""
Test try_fast_rg_curve() -- fast reload of a previously-exported Rg curve
from optimized/rg-curve/, skipping the per-frame Guinier fit.
"""
import pytest
import tempfile
import shutil
from pathlib import Path

from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD
from molass.Rigorous.CurrentStateUtils import try_fast_rg_curve
from molass.Rigorous.RecipeRunner import rebuild_decomposition_from_recipe

pytestmark = pytest.mark.slow  # optimization_folder below runs a real DE optimization


@pytest.fixture(scope="module")
def corrected_ssd():
    """Load and prepare SAMPLE1 data."""
    ssd = SSD(SAMPLE1)
    trimmed = ssd.trimmed_copy()
    corrected = trimmed.corrected_copy()
    return corrected


@pytest.fixture(scope="module")
def optimization_folder(corrected_ssd):
    """Run a minimal optimization (which exports optimized/rg-curve/) and
    return the analysis folder.

    SLOW: module-scoped (built once for this file), but still a real DE run.
    """
    tmpdir = tempfile.mkdtemp(prefix="test_fast_rg_curve_")
    analysis_folder = str(Path(tmpdir) / "test_fast_rg_curve")

    try:
        decomp = corrected_ssd.quick_decomposition(num_components=2)
        decomp.optimize_rigorously(
            analysis_folder=analysis_folder,
            method='DE',
            niter=1,
            monitor=False,
        )
        yield analysis_folder
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_try_fast_rg_curve_loads_cached_curve(optimization_folder):
    """A freshly rebuilt decomposition gets its Rg curve populated from disk,
    without running a per-frame Guinier fit."""
    _ssd, _trimmed, decomp, _recipe = rebuild_decomposition_from_recipe(optimization_folder)

    assert not decomp.has_rg_curve

    ok = try_fast_rg_curve(decomp, optimization_folder)

    assert ok is True
    assert decomp.has_rg_curve
    rgcurve = decomp.get_rg_curve()
    assert len(rgcurve.indeces) == len(rgcurve.rgvalues) == len(rgcurve.scores)
    assert len(rgcurve.indeces) > 0


def test_try_fast_rg_curve_returns_false_without_export():
    """No optimized/rg-curve/ under this folder -- must fall back cleanly,
    not raise, and must not touch the decomposition's cache."""
    from molass_data import SAMPLE1
    ssd = SSD(SAMPLE1)
    trimmed = ssd.trimmed_copy()
    corrected = trimmed.corrected_copy()
    decomp = corrected.quick_decomposition(num_components=2)

    tmpdir = tempfile.mkdtemp(prefix="test_fast_rg_curve_empty_")
    try:
        ok = try_fast_rg_curve(decomp, tmpdir)
        assert ok is False
        assert not decomp.has_rg_curve
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
