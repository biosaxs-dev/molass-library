"""
Example of updating an existing test to use plot control
"""
import os
import matplotlib.pyplot as plt
from molass import get_version
get_version(toml_only=True)
from molass.Local import get_local_settings
from molass.Testing import show_or_save, configure_for_test, is_interactive

local_settings = get_local_settings()
TUTORIAL_DATA = local_settings['TUTORIAL_DATA']

@configure_for_test
def test_010_default():
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(TUTORIAL_DATA)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_copy = trimmed_ssd.corrected_copy()
    ssd.estimate_mapping()
    
    # Use is_interactive() to control debug parameter
    decomposition = ssd.quick_decomposition()
    decomposition.plot_components(debug=is_interactive())
    
    # If the plot_components method doesn't automatically handle show/save,
    # you can add this line:
    show_or_save("test_010_default")

if __name__ == "__main__":
    test_010_default()