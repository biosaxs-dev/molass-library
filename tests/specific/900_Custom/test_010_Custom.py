"""
    test Custom Data Loading and Visualization
"""
import os
import matplotlib.pyplot as plt
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
local_settings = get_local_settings()
TUTORIAL_DATA = local_settings['TUTORIAL_DATA']

def test_010_load_uv():
    from molass.DataUtils.UvLoader import load_uv
    file_path = os.path.join(TUTORIAL_DATA)
    uvM, wvector = load_uv(file_path)
    assert uvM.shape == (318, 574)
    assert wvector.shape == (318,)

def test_020_load_xr():
    from molass.DataUtils.XrLoader import load_xr
    xr_array, datafiles = load_xr(TUTORIAL_DATA)
    assert xr_array.shape == (287, 1176, 3)

def test_030_plot():
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(TUTORIAL_DATA)
    ssd.plot_compact(debug=True)