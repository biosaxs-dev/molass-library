"""
Data objects tutorial tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
import warnings
import os
from molass.Testing import control_matplotlib_plot

# Suppress matplotlib non-interactive backend warnings in batch mode
if os.environ.get('MOLASS_ENABLE_PLOTS', 'false').lower() == 'false':
    warnings.filterwarnings('ignore', message='.*non-interactive.*', category=UserWarning)

def show_or_close_plot():
    """Helper function to show plot in interactive mode or close in batch mode"""
    import matplotlib.pyplot as plt
    if os.environ.get('MOLASS_ENABLE_PLOTS', 'false').lower() == 'true':
        plt.show()
    else:
        plt.close()

# Global variables to share state between ordered tests
ssd = None

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_plot_3d():
    from molass import get_version
    assert get_version() >= '0.2.0', "This tutorial requires molass version 0.2.0 or higher."
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    global ssd
    ssd = SSD(SAMPLE1)
    ssd.plot_3d(title="3D Plot of Sample1");

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_plot_compact():
    ssd.plot_compact(title="Compact Plot of Sample1");

@pytest.mark.order(3)
@control_matplotlib_plot 
def test_003_plot_3d_section_lines():
    ssd.plot_3d(title="Section Lines where the 2D Plots Intersect", with_2d_section_lines=True);

@pytest.mark.order(4)
@control_matplotlib_plot
def test_004_plot_xr_curve():
    import matplotlib.pyplot as plt
    global xr_icurve
    xr_icurve = ssd.xr.get_icurve()
    plt.plot(xr_icurve.x, xr_icurve.y)
    plt.title('X-ray Intensity Elution Curve')
    plt.xlabel('Elution Time (or Volume)')
    plt.ylabel('Intensity')
    show_or_close_plot()

@pytest.mark.order(5)
@control_matplotlib_plot
def test_005_plot_uv_curve():
    import matplotlib.pyplot as plt
    global uv_icurve
    uv_icurve = ssd.uv.get_icurve()
    plt.plot(uv_icurve.x, uv_icurve.y)
    plt.title('UV Absorbance Elution Curve')
    plt.xlabel('Elution Time (or Volume)')
    plt.ylabel('Absorbance')
    show_or_close_plot()

@pytest.mark.order(6)
@control_matplotlib_plot
def test_006_plot_two_axes():
    import matplotlib.pyplot as plt
    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(12,5))
    ax1.plot(uv_icurve.x, uv_icurve.y)
    ax1.set_title('UV Absorbance')
    ax2.plot(xr_icurve.x, xr_icurve.y)
    ax2.set_title('X-ray Intensity')
    show_or_close_plot()

@pytest.mark.order(7)
def test_007_get_peaks():
    uv_peaks = uv_icurve.get_peaks()
    xr_peaks = xr_icurve.get_peaks()
    uv_peaks, xr_peaks
    assert uv_peaks == [131, 231], "Unexpected UV peak indices"   
    assert xr_peaks == [88, 157], "Unexpected X-ray peak indices"