"""
    test Trimming
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
import matplotlib.pyplot as plt
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
from molass_data import SAMPLE2

def test_010_PKS():
    from molass.DataObjects import SecSaxsData as SSD
    # path = os.path.join(DATA_ROOT_FOLDER, "20211222", "PKS")
    ssd = SSD(SAMPLE2)
    ssd.plot_trimming(debug=True)
    trimmed_ssd = ssd.trimmed_copy()
    trimmed_ssd.plot_trimming(debug=True)

if __name__ == "__main__":
    test_010_PKS()
    # plt.show()