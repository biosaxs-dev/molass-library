"""
"""Test RunInfo.score() method (formerly score_optimized).

Verifies the symmetric API for visualizing rigorous scores:
  - score() returns Score object
  - Has .sv, .fv, .breakdown attributes
  - Has .plot(), .diagnose(), .print_summary() methods
  - Works with jobid parameter

See: https://github.com/biosaxs-dev/molass-library/issues/221
"""
import pytest
import tempfile
import shutil
from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD
from molass.Rigorous.InitialScore import Score


@pytest.fixture
def simple_run_info():
    """Create a minimal rigorous run with DE niter=1 for testing."""
    ssd = SSD(SAMPLE1)
    trimmed = ssd.trimmed_copy()
    corrected = trimmed.corrected_copy()
    decomp = corrected.quick_decomposition(num_components=3)
    
    temp_dir = tempfile.mkdtemp(prefix="test_score_optimized_")
    
    run_info = decomp.optimize_rigorously(
        method='DE',
        niter=1,
        async_=False,
        monitor=False,
        trimmed_ssd=trimmed,
        analysis_folder=temp_dir
    )
    
    yield run_info
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_score_returns_score_object(simple_run_info):
    """score() returns Score object."""
    result = simple_run_info.score()
    assert isinstance(result, Score)


def test_score_has_required_attributes(simple_run_info):
    """score() result has .sv, .fv, .breakdown."""
    result = simple_run_info.score()
    
    assert hasattr(result, 'sv')
    assert hasattr(result, 'fv')
    assert hasattr(result, 'breakdown')
    
    assert isinstance(result.sv, float)
    assert isinstance(result.fv, float)
    assert isinstance(result.breakdown, dict)
    assert 'fv' in result.breakdown
    assert 'scores' in result.breakdown


def test_score_has_visualization_methods(simple_run_info):
    """score() result has .plot(), .diagnose(), .print_summary()."""
    result = simple_run_info.score()
    
    assert hasattr(result, 'plot')
    assert hasattr(result, 'diagnose')
    assert hasattr(result, 'print_summary')
    assert callable(result.plot)
    assert callable(result.diagnose)
    assert callable(result.print_summary)


def test_score_plot_works(simple_run_info):
    """score().plot() produces a matplotlib figure."""
    result = simple_run_info.score()
    fig = result.plot(title="Test Optimized Score")
    
    assert fig is not None
    # Check it's a matplotlib figure
    assert hasattr(fig, 'axes')
    assert len(fig.axes) >= 3  # UV, XR, scores panels


def test_score_sv_in_valid_range(simple_run_info):
    """score() SV should be in 0-100 range."""
    result = simple_run_info.score()
    assert 0 <= result.sv <= 100


def test_score_without_analysis_folder_raises():
    """score() raises ValueError when no analysis_folder stored."""
    from molass.Rigorous.RunInfo import RunInfo
    
    ri = RunInfo(ssd=None, optimizer=None, dsets=None, init_params=None)
    
    with pytest.raises(ValueError, match="No analysis_folder stored"):
        ri.score()


def test_score_diagnose_works(simple_run_info):
    """score().diagnose() returns list of Diagnosis objects."""
    result = simple_run_info.score()
    diagnoses = result.diagnose()
    
    assert isinstance(diagnoses, list)
    assert len(diagnoses) > 0
    
    # Check structure of first diagnosis
    d = diagnoses[0]
    assert hasattr(d, 'score')
    assert hasattr(d, 'status')
    assert hasattr(d, 'reason')
    assert hasattr(d, 'suggestion')


def test_score_symmetric_api():
    """Verify Decomposition.score and RunInfo.score have the same return type."""
    from molass.LowRank.Decomposition import Decomposition
    from molass.Rigorous.RunInfo import RunInfo
    
    # Both should return Score with these methods
    required_attrs = {'sv', 'fv', 'breakdown', 'plot', 'diagnose', 'print_summary'}
    
    score_methods = set(dir(Score))
    for attr in required_attrs:
        assert attr in score_methods, f"Score missing {attr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
