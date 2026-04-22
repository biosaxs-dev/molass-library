"""
Data trimming tutorial tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
from molass.Testing import control_matplotlib_plot

# Global variables to share state between ordered tests
ssd = None

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_plot_3d():
    from molass import requires
    requires('0.2.0')
    from molass_data import SAMPLE2
    from molass.DataObjects import SecSaxsData as SSD
    global ssd
    ssd = SSD(SAMPLE2)
    ssd.plot_3d(title="3D Plot of Sample2");

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_plot_compact():
    ssd.plot_compact(title="Compact Plot of Sample2");

@pytest.mark.order(3)
@control_matplotlib_plot 
def test_003_plot_trimming():
    global trimmed_ssd
    trimmed_ssd = ssd.trimmed_copy()
    trimmed_ssd.plot_trimming(title="Sample2 - Trimmed");

@pytest.mark.order(4)
@control_matplotlib_plot
def test_004_plot_compact():
    trimmed_ssd.plot_compact(title="Sample2 - Trimmed");

@pytest.mark.order(5)
def test_005_make_trimming():
    trimming = ssd.make_trimming()
    print("Trimming:", trimming)
    xr = trimming.xr_slices
    uv = trimming.uv_slices
    # q-range is deterministic
    assert int(xr[0].start) == 12
    assert int(xr[0].stop) == 765
    # frame ranges may vary by Python/NumPy version (±80 tolerance)
    assert abs(int(xr[1].start) - 235) < 80, f"xr frame start unexpected: {xr[1].start}"
    assert abs(int(xr[1].stop) - 643) < 80, f"xr frame stop unexpected: {xr[1].stop}"
    assert uv[0] == slice(62, None)
    assert abs(int(uv[1].start) - 218) < 80, f"uv frame start unexpected: {uv[1].start}"
    assert abs(int(uv[1].stop) - 663) < 80, f"uv frame stop unexpected: {uv[1].stop}"

@pytest.mark.order(6)
@control_matplotlib_plot
def test_006_manual_trimming():
    global manually_trimmed_ssd
    manually_trimmed_ssd = ssd.copy(xr_slices=(slice(12, 765), slice(235-100, 643+100)),
                        uv_slices=(slice(62, None), slice(218-100, 668+100)),
                        trimmed=False  # to plot the original trimming ranges in the next plot 
                        )

@pytest.mark.order(7)
@control_matplotlib_plot
def test_007_plot_compact():
    manually_trimmed_ssd.plot_compact(title="SAMPLE2 - Manually Trimmed");