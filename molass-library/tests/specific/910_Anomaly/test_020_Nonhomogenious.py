"""
    test Nonhomogenious
"""
import os
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']

def test_010_XrLoader_Sample_CirAve():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, '20210519', 'Sample_CirAve')
    ssd = SSD(path)
    # ssd.plot_compact(title=path);