"""
Data correction tutorial tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
from molass.Testing import control_matplotlib_plot

# Global variables to share state between ordered tests
ssd = None
corrected_ssd = None

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_plot_compact():
    from molass import get_version
    assert get_version() >= '0.8.5', "This tutorial requires molass version 0.8.5 or higher."
    from molass_data import SAMPLE2
    from molass.DataObjects import SecSaxsData as SSD
    global ssd, trimmed_ssd
    ssd = SSD(SAMPLE2)
    trimmed_ssd = ssd.trimmed_copy()
    trimmed_ssd.plot_compact(baseline=True);

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_corrected_copy():
    global corrected_ssd
    corrected_ssd = trimmed_ssd.corrected_copy()
    corrected_ssd.plot_compact(baseline=True);

@pytest.mark.order(3)
def test_003_set_baseline_method():
    ssd.set_baseline_method('buffit')             # default for X-ray (v0.8.5+)
    ssd.set_baseline_method('linear')             # simpler global linear fit
    ssd.set_baseline_method(('buffit', 'uvdiff')) # recommended: buffit for X-ray, uvdiff for UV
    ssd.set_baseline_method(('linear', 'uvdiff'))
    ssd.set_baseline_method('integral')

@pytest.mark.order(4)
@control_matplotlib_plot
def test_004_set_baseline_method_uvdiff():
    trimmed_ssd.set_baseline_method(('buffit', 'uvdiff'))
    trimmed_ssd.plot_compact(baseline=True);

@pytest.mark.order(5)
@control_matplotlib_plot
def test_005_corrected_copy():
    global corrected_ssd
    corrected_ssd = trimmed_ssd.corrected_copy()
    corrected_ssd.plot_compact(baseline=True);

@pytest.mark.order(6)
def test_006_get_baseline_method():
    methods = corrected_ssd.get_baseline_method()
    print("Current baseline methods:", methods)
    assert methods == ('buffit', 'uvdiff'), "Unexpected baseline methods"

@pytest.mark.order(7)
@control_matplotlib_plot
def test_007_set_baseline_method_integral():
    trimmed_ssd.set_baseline_method('integral')
    trimmed_ssd.plot_compact(baseline=True);

@pytest.mark.order(8)
@control_matplotlib_plot
def test_008_corrected_copy_integral():
    global corrected_ssd
    corrected_ssd = trimmed_ssd.corrected_copy()
    corrected_ssd.plot_compact(baseline=True);

@pytest.mark.order(9)
def test_009_get_baseline_method():
    methods = corrected_ssd.get_baseline_method()
    print("Current baseline methods:", methods)
    assert methods == 'integral', "Unexpected baseline methods"