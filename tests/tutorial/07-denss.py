"""
Electron density retrieval tutorial tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
from molass.Testing import control_matplotlib_plot

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_plot_components():
    from molass import get_version
    assert get_version() >= '0.6.3', "This tutorial requires molass version 0.6.3 or higher."
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    global decomposition
    ssd = SSD(SAMPLE1)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy()
    decomposition = corrected_ssd.quick_decomposition(num_components=3)
    decomposition.plot_components() 

output_folder = "temp"

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_run_denss():
    import warnings
    from molass.SAXS.DenssTools import run_denss
    
    # Suppress deprecation warnings for this specific test
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        # Get, for example, the first component's scattering curve as an array
        jcurve_array = decomposition.get_xr_components()[0].get_jcurve_array()
        run_denss(jcurve_array, output_folder=output_folder)

@pytest.mark.order(3)
@control_matplotlib_plot
def test_003_show_mrc():
    import matplotlib.pyplot as plt
    from molass.SAXS.MrcViewer import show_mrc
    show_mrc(output_folder + '/denss_result.mrc');
