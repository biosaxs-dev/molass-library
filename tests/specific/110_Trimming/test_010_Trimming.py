"""
    test Trimming with Flowchanges
"""
import os
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
from molass.Testing import control_matplotlib_plot, is_interactive
local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']

@control_matplotlib_plot
def run_if_data_available(filename):
    import matplotlib.pyplot as plt
    from molass.DataObjects import SecSaxsData as SSD
    filepath = os.path.join(DATA_ROOT_FOLDER, filename)
    if not os.path.exists(filepath):
        print(f"Data file {filepath} not found. Skipping test.")
        return False
    ssd = SSD(filepath)
    ssd.plot_trimming(debug=is_interactive())
    trimmed_ssd = ssd.trimmed_copy()
    trimmed_ssd.plot_trimming(debug=is_interactive())
    plt.show()
    return True

@control_matplotlib_plot
def test_010_20160628():
    run_if_data_available('20160628')

if __name__ == "__main__":
    test_010_20160628()