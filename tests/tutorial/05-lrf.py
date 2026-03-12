"""
Low rank factorization tutorial tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
from molass.Testing import control_matplotlib_plot

# Global variables to share state between ordered tests
ssd = None
trimmed_ssd = None

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_plot_compact():
    from molass import requires
    requires('0.6.0')
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    global ssd
    ssd = SSD(SAMPLE1)
    ssd.plot_compact();

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_quick_decomposition():
    global corrected_ssd
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy()
    decomposition = corrected_ssd.quick_decomposition()
    plot1 = decomposition.plot_components()

@pytest.mark.order(3)
@control_matplotlib_plot
def test_003_quick_decomposition_3_components():
    global decomposition3
    decomposition3 = corrected_ssd.quick_decomposition(num_components=3)
    plot2 = decomposition3.plot_components(title="Decomposition of Sample1 (num_components=3)") 

@pytest.mark.order(4)
@control_matplotlib_plot
def test_004_get_proportions():
    proportions = decomposition3.get_proportions()
    print("Current proportions:", proportions)
    expected = [0.39588467, 0.12442568, 0.47968965]
    assert proportions == pytest.approx(expected, abs=1e-2)

@pytest.mark.order(5)
@control_matplotlib_plot
def test_005_quick_decomposition_proportions():
    modified_decomposition = corrected_ssd.quick_decomposition(num_components=3, proportions=[0.32, 0.20, 0.48])
    plot2 = modified_decomposition.plot_components(title="Modified Decomposition of Sample1 (num_components=3, proportions=[0.32, 0.20, 0.48])") 

@pytest.mark.order(6)
def test_006_another_sample():
    from molass.DataObjects import SecSaxsData as SSD
    from molass_data import SAMPLE2
    global corrected_ssd2
    ssd2 = SSD(SAMPLE2)
    trimmed_ssd2 = ssd2.trimmed_copy()
    corrected_ssd2 = trimmed_ssd2.corrected_copy()

@pytest.mark.order(7)
@control_matplotlib_plot
def test_007_quick_decomposition():
    decomposition23 = corrected_ssd2.quick_decomposition(num_components=3)
    plot4 = decomposition23.plot_components(title="Decomposition of Sample2 (num_components=3)")

@pytest.mark.order(8)
@control_matplotlib_plot
def test_008_quick_decomposition_num_plates():
    decomposition23n = corrected_ssd2.quick_decomposition(num_components=3, num_plates=14400)   # 14400 = 48000 * 30cm/100cm
    plot5 = decomposition23n.plot_components(title="Decomposition of Sample2 (num_components=3, num_plates=14400)")

@pytest.mark.order(9)
def test_009_another_sample():
    from molass.DataObjects import SecSaxsData as SSD
    from molass_data import SAMPLE3
    global ssd3
    ssd3 = SSD(SAMPLE3)

@pytest.mark.order(10)
@control_matplotlib_plot
def test_010_quick_decomposition_rank_1():
    global decomposition31
    decomposition31 = ssd3.quick_decomposition()
    plot6 = decomposition31.plot_components(title="Sample3 as rank 1")

@pytest.mark.order(11)
@control_matplotlib_plot
def test_011_quick_decomposition_rank_2():
    decomposition31.update_xr_ranks(ranks=[2]) 
    plot6 = decomposition31.plot_components(title="SAMPLE3 as rank 2")

@pytest.mark.order(12)
def test_012_align_decompositions():
    """align_decompositions() returns a common q-grid and interpolated P matrices."""
    import numpy as np
    import molass
    from molass_data import SAMPLE1, SAMPLE2
    from molass.DataObjects import SecSaxsData as SSD

    d1 = SSD(SAMPLE1).trimmed_copy().corrected_copy().quick_decomposition()
    d2 = SSD(SAMPLE2).trimmed_copy().corrected_copy().quick_decomposition()

    q_common, P1, P2 = molass.align_decompositions(d1, d2, n=300, normalize=True)

    # q_common has the requested length and is strictly increasing
    assert len(q_common) == 300
    assert np.all(np.diff(q_common) > 0)

    # P matrices are on the same q-grid (same number of rows)
    assert P1.shape[0] == 300
    assert P2.shape[0] == 300

    # normalize=True → each column peaks at 1
    assert np.allclose(P1.max(axis=0), 1.0)
    assert np.allclose(P2.max(axis=0), 1.0)

    # get_P_at gives same result as align_decompositions for one decomposition
    P1_direct = d1.get_P_at(q_common, normalize=True)
    assert np.allclose(P1, P1_direct)

    print(f"q_common: [{q_common[0]:.4f}, {q_common[-1]:.4f}] Å⁻¹  ({len(q_common)} pts)")
    print(f"P1 shape: {P1.shape},  P2 shape: {P2.shape}")

@pytest.mark.order(13)
def test_013_component_quality_scores():
    """component_quality_scores() and is_component_reliable() detect spurious components."""
    import math
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD

    ssd = SSD(SAMPLE1).trimmed_copy().corrected_copy()

    # Natural decomposition (2 components): both should be reliable
    d2 = ssd.quick_decomposition(num_components=2)
    scores2 = d2.component_quality_scores()
    print(f"SAMPLE1 2-component scores: {scores2}")
    assert len(scores2) == 2
    assert all(isinstance(s, float) for s in scores2)
    assert all(d2.is_component_reliable(i) for i in range(2)), \
        f"All natural components should be reliable, got scores: {scores2}"

    # Forced 3-component decomposition: the extra component should score lower
    d3 = ssd.quick_decomposition(num_components=3)
    scores3 = d3.component_quality_scores()
    print(f"SAMPLE1 3-component (forced) scores: {scores3}")
    assert len(scores3) == 3
    # At least one component should score lower than in the natural decomposition
    assert min(scores3) < min(scores2), \
        f"Forced extra component should lower minimum score: {scores3} vs {scores2}"

    # nan Rg always causes score = 0
    from unittest.mock import MagicMock, patch
    from molass.LowRank.ComponentReliability import component_quality_scores as cqs
    stub_decomp = MagicMock()
    stub_decomp.get_rgs.return_value = [15.0, float('nan')]
    stub_decomp.get_proportions.return_value = [0.6, 0.4]
    scores_nan = cqs(stub_decomp)
    assert scores_nan[1] == 0.0, "nan Rg must give score 0.0"
    assert not math.isnan(scores_nan[0]), "Valid Rg must give a numeric score"
    print(f"nan-Rg mock scores: {scores_nan}")
