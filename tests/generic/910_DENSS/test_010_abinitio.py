"""
    test DenssTools
"""
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass_data import SAMPLE1

import pytest
from molass.DataObjects import SecSaxsData as SSD

ssd_instance = SSD(SAMPLE1)

def test_01_constructor():
    assert ssd_instance is not None, "SSD object should not be None"
    assert hasattr(ssd_instance, 'xr'), "SSD object should have 'xr' attribute"
    assert hasattr(ssd_instance, 'uv'), "SSD object should have 'uv' attribute"

def test_02_exec_denss():
    from molass.SAXS.DenssTools import run_denss
    trimmed_ssd = ssd_instance.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy()
    data = corrected_ssd.xr.get_jcurve_array()
    run_denss(data, output_folder="temp")

if __name__ == "__main__":
    # path = '::'.join([__file__, 'test_02_exec_denss'])
    # pytest.main([path, '-v', '--tb=short'])
    ssd = SSD(SAMPLE1)
    test_02_exec_denss(ssd)