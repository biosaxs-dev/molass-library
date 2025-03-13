"""
    Test.TestPeaklike.py

    cf. https://realpython.com/python-unittest/
"""
import sys
import os
testdir = os.path.dirname(__file__)
libhome = os.path.dirname(os.path.dirname(testdir))
sys.path.insert(0, libhome)

import unittest
from molass.Test.TestSettings import get_datafolder

class TestPeaklike(unittest.TestCase):
    def __init__(self, methodName='runTest'):  
        super().__init__(methodName)
        self.root_folder = get_datafolder()

    def test_check_peaklike_segment(self):
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
            path = os.path.join(self.root_folder, folder)
            print([k], "path=", path)
            c1, c2 = get_uvcurves(path)
            points, segments = get_segments(c2.x, c2.y, n_bkps=3)
            mt = Moment(c1.x, c1.y)
            ret, sign = check_peaklike_segment(c2.x, c2.y, mt, points, segments)
            self.assertEqual((k, ret[2:4]), (k, result))   # using k in order to identify the case when it fails

        test_pairs_4 = [
            (r"20170209\OA_Ald_Fer",        ( 90, 205)),    # 0
            (r"20180219",                   (345, 430)),    # 1
            (r"20190524_1",                 (205, 250)),    # 2
        ]
        for k, (folder, result) in enumerate(test_pairs_4):
            path = os.path.join(self.root_folder, folder)
            print([k], "path=", path)
            c1, c2 = get_uvcurves(path)
            points, segments = get_segments(c2.x, c2.y, n_bkps=4)
            mt = Moment(c1.x, c1.y)
            ret, sign = check_peaklike_segment(c2.x, c2.y, mt, points, segments)
            self.assertEqual((k, ret[2:4]), (k, result))   # using k in order to identify the case when it fails

if __name__ == '__main__':
    unittest.main()