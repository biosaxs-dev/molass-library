"""
Nontrivial decomposition retrieval tutorial tests with controlled execution order.
Requires: pip install pytest-order
"""

import numpy as np
import pytest
from molass.Testing import control_matplotlib_plot

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_plot_compact():
    from molass import get_version
    assert get_version() >= '0.6.0', "This tutorial requires molass version 0.6.0 or higher."
    from molass_data import get_version
    assert get_version() >= '0.3.0', "This tutorial requires molass_data version 0.3.0 or higher."
    from molass_data import SAMPLE4
    from molass.DataObjects import SecSaxsData as SSD
    global corrected_ssd
    ssd = SSD(SAMPLE4)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy()
    corrected_ssd.plot_compact();

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_run_denss():
    global rgcurve
    rgcurve = corrected_ssd.xr.compute_rgcurve()
    decomposition = corrected_ssd.quick_decomposition(num_components=2)
    decomposition.plot_components(rgcurve=rgcurve)

num_trails = 8
species1_proportions = np.ones(num_trails) * 3
species2_proportions = np.linspace(1, 3, num_trails)

@pytest.mark.order(3)
@control_matplotlib_plot
def test_003_binary_proportions():
    global proportions
    proportions = np.array([species1_proportions, species2_proportions]).T
    print("Current proportions:", proportions)

@pytest.mark.order(4)
@control_matplotlib_plot
def test_004_plot_varied_decompositions():
    corrected_ssd.plot_varied_decompositions(proportions, rgcurve=rgcurve, best=3)

@pytest.mark.order(5)
@control_matplotlib_plot
def test_005_tertiary_proportions():
    import numpy as np
    global proportions
    species3_proportions = np.ones(num_trails) * 1
    proportions = np.array([species1_proportions, species2_proportions, species3_proportions]).T
    print("Current proportions:", proportions)

@pytest.mark.order(6)
@control_matplotlib_plot
def test_006_plot_varied_decompositions():
    corrected_ssd.plot_varied_decompositions(proportions, rgcurve=rgcurve, best=3)
