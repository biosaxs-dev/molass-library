"""
    test Mapping
"""
import os
import matplotlib.pyplot as plt
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']

def test_010_OA_ALD_201():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20220716", "OA_ALD_201")
    ssd = SSD(path)
    mapping = ssd.estimate_mapping(debug=True)
    ssd.plot_compact(debug=True)

def test_020_20160227():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20160227", "backsub")
    ssd = SSD(path)
    mapping = ssd.estimate_mapping(debug=True)
    ssd.plot_compact(debug=True)

def test_030_20160628():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20160628")
    ssd = SSD(path)
    mapping = ssd.estimate_mapping(debug=True)
    ssd.plot_compact(debug=True)

def test_040_Kosugi3a():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20161119", "Kosugi3a_BackSub")
    ssd = SSD(path)
    mapping = ssd.estimate_mapping(debug=False)
    ssd.plot_compact(debug=True)

def test_050_proteins5():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20191006_proteins5")
    ssd = SSD(path)
    mapping = ssd.estimate_mapping(debug=True)
    ssd.plot_compact(debug=True)

def test_060_20201006_1():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20201006_1")
    ssd = SSD(path)
    mapping = ssd.estimate_mapping(debug=True)
    ssd.plot_compact(debug=True)
