"""
Rank estimation tutorial tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
from molass.Testing import control_matplotlib_plot

# Global variables to share state between ordered tests
corrected_ssd = None

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_plot_components():
    from molass import get_version
    assert get_version() >= '0.2.0', "This script requires molass version 0.2.0 or higher."
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    global corrected_ssd
    ssd = SSD(SAMPLE1)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy()
    decomposition = corrected_ssd.quick_decomposition();
    decomposition.plot_components();

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_quick_decomposition():
    global decomposition_nc3
    decomposition_nc3 = corrected_ssd.quick_decomposition(num_components=3)
    decomposition_nc3.plot_components();

@pytest.mark.order(3)
@control_matplotlib_plot
def test_003_ratio_curve():
    corrected_ssd.plot_compact(ratio_curve=True, title="Tutorial Data - Compact Plot with Ratio Curve");

@pytest.mark.order(4)
def test_004_compute_scds():
    global scds
    scds = decomposition_nc3.compute_scds()
    print("Current SCDs:", scds)
    expected = [0.5141964, 4.135358, 0.6386071]
    assert scds == pytest.approx(expected, abs=1e-2)

@pytest.mark.order(5)
def test_005_scd_to_rank():
    from molass.Backward.RankEstimator import scd_to_rank
    ranks = [scd_to_rank(scd) for scd in scds]
    expected_ranks = [1, 1, 1]
    for scd, rank, expected_rank in zip(scds, ranks, expected_ranks):
        print(f"SCD: {scd}, Rank: {rank}")
        assert rank == expected_rank, f"Unexpected rank for SCD {scd}: got {rank}, expected {expected_rank}"

@pytest.mark.order(6)
@control_matplotlib_plot
def test_006_another_sample():
    from molass.DataObjects import SecSaxsData as SSD
    from molass_data import SAMPLE3
    global scds
    ssd3 = SSD(SAMPLE3)
    decomposition3 = ssd3.quick_decomposition()
    scds = decomposition3.compute_scds()
    assert scds == pytest.approx([5.136732], abs=1e-2)

@pytest.mark.order(7)
@control_matplotlib_plot
def test_007_scd_to_rank():
    from molass.Backward.RankEstimator import scd_to_rank
    ranks = [scd_to_rank(scd) for scd in scds]
    expected_ranks = [2]
    for scd, rank, expected_rank in zip(scds, ranks, expected_ranks):
        print(f"SCD: {scd}, Rank: {rank}")
        assert rank == expected_rank, f"Unexpected rank for SCD {scd}: got {rank}, expected {expected_rank}"