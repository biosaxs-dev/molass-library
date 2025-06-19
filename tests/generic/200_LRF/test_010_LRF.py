"""
    test LRF
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
import matplotlib.pyplot as plt
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']
TUTORIAL_DATA = local_settings['TUTORIAL_DATA']

def test_010_LRF():
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(TUTORIAL_DATA)
    ssd.estimate_mapping()
    lr_info = ssd.quick_lowrank_info(num_components=3)
    lr_info.plot_components(debug=True)


if __name__ == "__main__":
    test_010_LRF()
    # plt.show()