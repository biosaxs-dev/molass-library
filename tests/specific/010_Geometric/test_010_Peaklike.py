"""
    test Peaklike
"""
import os
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']

def test_010_check_peaklike_segment():
    from molass.DataUtils.UvLoader import get_uvcurves
    from molass.Geometric.Linesegment import get_segments
    from molass.Stats.Moment import Moment
    from molass.Geometric.Peaklike import check_peaklike_segment
    test_pairs_3 = [
        (r"20170209\OA_Ald_Fer",        ( 90, 205)),    # 0
        (r"20180219",                   (320, 460)),    # 1
        (r"20190524_1",                 (210, 410)),    # 2
    ]
    for k, (folder, result) in enumerate(test_pairs_3):
        path = os.path.join(DATA_ROOT_FOLDER, folder)
        print([k], "path=", path)
        c1, c2 = get_uvcurves(path)
        points, segments = get_segments(c2.x, c2.y, n_bkps=3)
        mt = Moment(c1.x, c1.y)
        ret, sign = check_peaklike_segment(c2.x, c2.y, mt, points, segments)
        assert (k, ret[2:4]) == (k, result), ""    # using k in order to identify the case when it fails

    test_pairs_4 = [
        (r"20170209\OA_Ald_Fer",        ( 90, 205)),    # 0
        (r"20180219",                   (345, 430)),    # 1
        (r"20190524_1",                 (205, 250)),    # 2
    ]
    for k, (folder, result) in enumerate(test_pairs_4):
        path = os.path.join(DATA_ROOT_FOLDER, folder)
        print([k], "path=", path)
        c1, c2 = get_uvcurves(path)
        points, segments = get_segments(c2.x, c2.y, n_bkps=4)
        mt = Moment(c1.x, c1.y)
        ret, sign = check_peaklike_segment(c2.x, c2.y, mt, points, segments)
        assert (k, ret[2:4]) == (k, result), ""   # using k in order to identify the case when it fails