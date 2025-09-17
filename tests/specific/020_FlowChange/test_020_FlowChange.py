"""
    test FlowChange
"""
import os
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Global.Options import set_molass_options
set_molass_options(flowchange='auto')
# set_molass_options(flowchange=True)
from molass.Local import get_local_settings
local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']

def test_010_20171203():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20171203")
    ssd = SSD(path)
    print("Beamline:", ssd.beamline_info.name)
    mapping = ssd.estimate_mapping(debug=False)
    ssd.plot_compact(debug=True)

def test_011_20171203():
    from molass.DataUtils.UvLoader import get_uvcurves
    from molass.FlowChange.FlowChange import flowchange_exclude_slice
    path = os.path.join(DATA_ROOT_FOLDER, "20171203")
    c1, c2= get_uvcurves(path)
    i, j = flowchange_exclude_slice(c1, c2, debug=True)[0]
    assert (i,j) == (275, None)

def test_020_20201127_2():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20201127_2")
    ssd = SSD(path)
    print("Beamline:", ssd.beamline_info.name)
    mapping = ssd.estimate_mapping(debug=False)
    ssd.plot_compact(debug=True)

def test_021_20201127_2():
    from molass.DataUtils.UvLoader import get_uvcurves
    from molass.FlowChange.FlowChange import flowchange_exclude_slice
    path = os.path.join(DATA_ROOT_FOLDER, "20201127_2")
    c1, c2= get_uvcurves(path)
    i, j = flowchange_exclude_slice(c1, c2, debug=True)[0]
    assert (i,j) == (None, None)

def test_022_20201127_3():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20201127_3")
    ssd = SSD(path)
    print("Beamline:", ssd.beamline_info.name)
    mapping = ssd.estimate_mapping(debug=False)
    ssd.plot_compact(debug=True)

def test_030_20210323_1():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20210323_1")
    ssd = SSD(path)
    print("Beamline:", ssd.beamline_info.name)
    mapping = ssd.estimate_mapping(debug=False)
    ssd.plot_compact(debug=True)

def test_031_20210323_1():
    from molass.DataUtils.UvLoader import get_uvcurves
    from molass.FlowChange.FlowChange import flowchange_exclude_slice
    path = os.path.join(DATA_ROOT_FOLDER, "20210323_1")
    c1, c2= get_uvcurves(path)
    i, j = flowchange_exclude_slice(c1, c2, debug=True)[0]
    assert (i,j) == (None, None)
