"""
Quick start tutorial tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
from molass.Testing import control_matplotlib_plot

# Global variables to share state between ordered tests
ssd = None
decomposition = None

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_plot_3d():
    from molass import get_version
    assert get_version() >= '0.6.1', "This tutorial requires molass version 0.6.1 or higher."
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    global ssd
    ssd = SSD(SAMPLE1)
    assert ssd is not None
    ssd.plot_3d(title="3D Plot of Sample1");

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_plot_components():
    global decomposition
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy()
    decomposition = corrected_ssd.quick_decomposition()
    decomposition.plot_components(title="Decomposition of Sample1");

output_folder = "temp"
@pytest.mark.order(3)
@control_matplotlib_plot
def test_003_run_denss():
    import warnings
    from molass.SAXS.DenssTools import run_denss
    
    # Suppress deprecation warnings for this specific test
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        # Get, for example, the first component's scattering curve as an array
        jcurve_array = decomposition.get_xr_components()[0].get_jcurve_array()
        run_denss(jcurve_array, output_folder=output_folder)

@pytest.mark.order(4)
@control_matplotlib_plot
def test_004_show_mrc():
    import matplotlib.pyplot as plt
    from molass.SAXS.MrcViewer import show_mrc
    # Uncomment the following magic command line if you want to use an interactive plot in Jupyter Notebook
    # %matplotlib widget
    show_mrc(output_folder + '/denss_result.mrc');
    plt.close('all')  # Close the plot to avoid display during automated tests