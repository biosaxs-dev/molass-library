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
from molass.Global.Options import set_molass_options, get_molass_options
set_molass_options(flowchange='auto')
print("Current flowchange option:", get_molass_options('flowchange'))

@control_matplotlib_plot
def run_if_data_available(filename):
    import matplotlib.pyplot as plt
    from molass.DataObjects import SecSaxsData as SSD
    filepath = os.path.join(DATA_ROOT_FOLDER, filename)
    print(f"Checking for data file: {filepath}")
    if not os.path.exists(filepath):
        print(f"Data file {filepath} not found. Skipping test.")
        return False
    ssd = SSD(filepath)
    print("Beamline name:", ssd.get_beamline_name())
    ssd.plot_trimming(debug=is_interactive())
    trimmed_ssd = ssd.trimmed_copy()
    trimmed_ssd.plot_trimming(debug=is_interactive())
    plt.show()
    return True

@control_matplotlib_plot
def test_010_20160628():
    run_if_data_available('20160628')

@control_matplotlib_plot
def test_020_20180605_Backsub3():
    # This dataset has illegal lines that cause loading errors
    # Illegal files are now skipped in XrLoader.py
    run_if_data_available(r'20180605/Backsub3')

if __name__ == "__main__":
    test_010_20160628()