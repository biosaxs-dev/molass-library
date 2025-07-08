"""
    test Baseline Correction
"""
import os
import sys
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, repo_root)
import matplotlib.pyplot as plt
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']

def test_010_OA_Ald_default():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE1)
    ssd.plot_compact(baseline=True, debug=True)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy(debug=True)
    corrected_ssd.plot_compact(baseline=True, debug=True)

def test_020_OA_Ald_uvdiff():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE1)
    ssd.set_baseline_method(('linear', 'uvdiff'))
    ssd.plot_compact(baseline=True, debug=True)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy(debug=True)
    corrected_ssd.plot_compact(baseline=True, debug=True)

def test_031_OA_Ald_integral():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE1)
    ssd.set_baseline_method('integral')
    ssd.plot_compact(baseline=True, debug=True)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy(debug=True)
    corrected_ssd.plot_compact(baseline=True, debug=True)

def test_032_SAMPLE2_integral():
    from molass_data import SAMPLE2
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE2)
    ssd.set_baseline_method('integral')
    ssd.plot_compact(baseline=True, debug=True)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy(debug=True)
    corrected_ssd.plot_compact(baseline=True, debug=True)

if __name__ == "__main__":
    # test_010_OA_Ald_default()
    # test_020_OA_Ald_uvdiff()
    # test_031_OA_Ald_integral()
    test_032_SAMPLE2_integral()
    # plt.show()