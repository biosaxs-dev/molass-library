"""
    test Trimming
"""
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass_data import SAMPLE2
from molass.Testing import control_matplotlib_plot, is_interactive

@control_matplotlib_plot
def test_010_PKS():
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE2)
    ssd.plot_trimming(debug=is_interactive())
    trimmed_ssd = ssd.trimmed_copy()
    trimmed_ssd.plot_trimming(debug=is_interactive())

if __name__ == "__main__":
    test_010_PKS()