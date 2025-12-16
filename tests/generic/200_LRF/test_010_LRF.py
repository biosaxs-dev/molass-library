"""
    test LRF
"""
import pytest
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD
from molass.Testing import control_matplotlib_plot, is_interactive

def corrected_ssd_instance_():
    ssd = SSD(SAMPLE1)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_copy = trimmed_ssd.corrected_copy()
    return corrected_copy

corrected_ssd_instance = corrected_ssd_instance_()

@control_matplotlib_plot
def test_010_default():
    ssd = corrected_ssd_instance
    ssd.estimate_mapping()
    decomposition = ssd.quick_decomposition()
    decomposition.plot_components(debug=is_interactive())

@control_matplotlib_plot
def test_020_num_components():
    ssd = corrected_ssd_instance
    ssd.estimate_mapping()
    decomposition = ssd.quick_decomposition(num_components=3)
    decomposition.plot_components(debug=is_interactive())

if __name__ == "__main__":
    test_010_default()
    # plt.show()