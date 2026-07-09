"""
Test RunInfo.restore() factory function (issue #222).

Tests the unified cross-session loading API introduced to replace
the asymmetric load_best_rigorous_result() method.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
import warnings

from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD
from molass.Rigorous.RunInfo import restore, RunInfo
from molass.LowRank.Decomposition import Decomposition


@pytest.fixture(scope="module")
def corrected_ssd():
    """Load and prepare SAMPLE1 data."""
    ssd = SSD(SAMPLE1)
    trimmed = ssd.trimmed_copy()
    corrected = trimmed.corrected_copy()
    return corrected


@pytest.fixture(scope="module")
def optimization_folder(corrected_ssd):
    """Run a minimal optimization and return the analysis folder."""
    tmpdir = tempfile.mkdtemp(prefix="test_restore_")
    analysis_folder = str(Path(tmpdir) / "test_restore")
    
    try:
        decomp = corrected_ssd.quick_decomposition(num_components=2)
        # Run a minimal optimization
        run = decomp.optimize_rigorously(
            analysis_folder=analysis_folder,
            method='DE',
            niter=1,
            monitor=False
        )
        yield analysis_folder
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_restore_returns_runinfo(corrected_ssd, optimization_folder):
    """Test that restore() returns a RunInfo object."""
    decomp = corrected_ssd.quick_decomposition(num_components=2)
    run = restore(decomp, optimization_folder)
    
    assert isinstance(run, RunInfo), "restore() should return RunInfo instance"


def test_restore_sets_attributes(corrected_ssd, optimization_folder):
    """Test that restore() sets required attributes."""
    decomp = corrected_ssd.quick_decomposition(num_components=2)
    run = restore(decomp, optimization_folder)
    
    # Required attributes for cross-session use
    assert run.analysis_folder == optimization_folder
    assert run.decomposition is decomp
    assert run.ssd is decomp.ssd
    
    # Optimizer state (not available cross-session)
    assert run.optimizer is None
    assert run.dsets is None
    assert run.init_params is None


def test_restore_preserves_rgcurve(corrected_ssd, optimization_folder):
    """Test that restore() preserves rgcurve when provided."""
    rgcurve = corrected_ssd.get_rg_curve()
    decomp = corrected_ssd.quick_decomposition(num_components=2, rgcurve=rgcurve)
    run = restore(decomp, optimization_folder, rgcurve=rgcurve)
    
    assert run.rgcurve is rgcurve, "restore() should preserve rgcurve"


def test_restore_load_best_works(corrected_ssd, optimization_folder):
    """Test that load_best() works on restored RunInfo."""
    decomp = corrected_ssd.quick_decomposition(num_components=2)
    run = restore(decomp, optimization_folder)
    
    # load_best() should work cross-session
    result = run.load_best()
    
    # Verify we got a Decomposition back
    assert isinstance(result, Decomposition)
    assert len(result.xr_ccurves) == 2


def test_restore_live_status_works(corrected_ssd, optimization_folder):
    """Test that live_status() works on restored RunInfo."""
    decomp = corrected_ssd.quick_decomposition(num_components=2)
    run = restore(decomp, optimization_folder)
    
    # live_status() should work cross-session
    status = run.live_status()
    
    # Verify status dict structure
    assert 'phase' in status
    assert 'best_fv' in status
    assert 'best_sv' in status
    assert status['analysis_folder'] == optimization_folder


def test_load_best_rigorous_result_deprecated(corrected_ssd, optimization_folder):
    """Test that load_best_rigorous_result() emits DeprecationWarning."""
    decomp = corrected_ssd.quick_decomposition(num_components=2)
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = decomp.load_best_rigorous_result(optimization_folder)
        
        # Check that a DeprecationWarning was raised
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "load_best_rigorous_result() is deprecated" in str(w[0].message)
        assert "restore()" in str(w[0].message)
        
        # Verify it still works (backward compat)
        assert isinstance(result, Decomposition)


def test_restore_unified_api_pattern(corrected_ssd, optimization_folder):
    """Test the unified API pattern works for both paths."""
    decomp = corrected_ssd.quick_decomposition(num_components=2)
    
    # Cross-session path using restore()
    run = restore(decomp, optimization_folder)
    result = run.load_best()
    
    # Verify unified interface: both return Decomposition
    assert isinstance(result, Decomposition)
    
    # Both should have the same load_best() interface
    assert hasattr(run, 'load_best')
    assert hasattr(run, 'live_status')
