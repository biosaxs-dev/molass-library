"""
    test LRF
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
import pytest
import matplotlib.pyplot as plt
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']
TUTORIAL_DATA = local_settings['TUTORIAL_DATA']
from molass.DataObjects import SecSaxsData as SSD

@pytest.fixture(scope="module")
def corrected_ssd_instance():
    print("Fixture executed")
    ssd = SSD(TUTORIAL_DATA)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_copy = trimmed_ssd.corrected_copy()
    return corrected_copy

def test_010_default(corrected_ssd_instance):
    ssd = corrected_ssd_instance
    ssd.estimate_mapping()
    decomposition = ssd.quick_decomposition()
    decomposition.plot_components(debug=True)

def test_020_num_components(corrected_ssd_instance):
    ssd = corrected_ssd_instance
    ssd.estimate_mapping()
    decomposition = ssd.quick_decomposition(num_components=3)
    decomposition.plot_components(debug=True)

if __name__ == "__main__":
    test_010_default()
    # plt.show()