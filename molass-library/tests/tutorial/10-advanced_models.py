"""
Advanced models tutorial tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
from molass.Testing import control_matplotlib_plot

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_plot_compact():
    from molass import get_version
    assert get_version() >= '0.6.0', "This tutorial requires molass version 0.6.0 or higher."
    from molass_data import SAMPLE4
    from molass.DataObjects import SecSaxsData as SSD
    global decomposition
    ssd = SSD(SAMPLE4)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy()
    decomposition = corrected_ssd.quick_decomposition(proportions=[3., 1.85714286, 1.])
    decomposition.plot_components(title="EGH decomposition of sample4 with proportions [3, 1.86, 1]");

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_optimize_with_model_sdm():
    sdm_decomposition = decomposition.optimize_with_model('SDM')
    sdm_decomposition.plot_components(title="SDM decomposition of sample4 from EGH result");

@pytest.mark.order(3)
@control_matplotlib_plot
def test_003_optimize_with_model_edm():
    import warnings
    # Suppress runtime warnings for this specific test
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        edm_decomposition = decomposition.optimize_with_model('EDM')
        edm_decomposition.plot_components(title="EDM decomposition of sample4 from EGH result");