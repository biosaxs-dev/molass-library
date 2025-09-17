"""
    test Bubbles
"""
import os
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']
Sugiyama = os.path.join(DATA_ROOT_FOLDER, "20170226","Sugiyama")

def test_010_load_xr():
    from molass.DataUtils.XrLoader import load_xr, xr_remove_bubbles 
    xr_array, datafiles = load_xr(Sugiyama)
    assert xr_array.shape == (367, 1157, 3), "xr_array.shape should be (367, 1157, 3)"
    xr_remove_bubbles(xr_array, debug=True)

def test_020_SSD():
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(Sugiyama, remove_bubbles=True)
    ssd.plot_compact()