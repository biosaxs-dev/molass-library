"""
    test SSD
"""
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass_data import SAMPLE1

import pytest
from molass.DataObjects import SecSaxsData as SSD

@pytest.fixture(scope="module")
def ssd_instance():
    print("Fixture executed")
    return SSD(SAMPLE1)

def test_01_constructor(ssd_instance):
    assert ssd_instance is not None, "SSD object should not be None"
    assert hasattr(ssd_instance, 'xr'), "SSD object should have 'xr' attribute"
    assert hasattr(ssd_instance, 'uv'), "SSD object should have 'uv' attribute"

def test_02_plot_3d(ssd_instance):
    plot_result = ssd_instance.plot_3d()
    assert plot_result is not None, "Plot result should not be None"
    plot_result = ssd_instance.plot_3d(uv_only=True)
    assert plot_result is not None, "Plot result should not be None"
    plot_result = ssd_instance.plot_3d(xr_only=True)
    assert plot_result is not None, "Plot result should not be None"