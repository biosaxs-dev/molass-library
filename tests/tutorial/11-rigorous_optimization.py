"""
Tests for the rigorous optimization tutorial (tutorial 11).
"""

import pytest
from molass.Testing import control_matplotlib_plot

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_quick_decomposition():
    from molass import get_version
    assert get_version() >= '0.7.5', "this notebook requires molass v0.7.5 or higher."
    from molass_data import SAMPLE4
    from molass.DataObjects import SecSaxsData as SSD
    global decomposition, rgcurve
    ssd = SSD(SAMPLE4)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy()
    decomposition = corrected_ssd.quick_decomposition(proportions=[0.2, 0.5, 0.3])
    rgcurve = corrected_ssd.xr.compute_rgcurve()
    decomposition.plot_components(title="EGH Decomposition", rgcurve=rgcurve)

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_rigorous_optimization():
    from time import sleep
    global run_info
    run_info = decomposition.optimize_rigorously(rgcurve=rgcurve, analysis_folder="temp_analysis_egh", method='NS', niter=20)
    current_decomposition = run_info.get_current_decomposition(wait_for_first_results=True)
    current_decomposition.plot_components(title="Rigorous Optimization Result", rgcurve=rgcurve)
    run_info.monitor.terminate()
