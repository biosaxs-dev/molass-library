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
    from molass import get_version
    assert get_version() >= '0.6.0', "This tutorial requires molass version 0.6.0 or higher."
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
