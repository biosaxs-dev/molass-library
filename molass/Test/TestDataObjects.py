"""
    Test.TestDataObjects.py

    cf. https://realpython.com/python-unittest/
"""
import sys
import os
testdir = os.path.dirname(__file__)
libhome = os.path.dirname(os.path.dirname(testdir))
sys.path.insert(0, libhome)

import unittest
import numpy as np
from molass.Test.TestSettings import get_datafolder

class TestDataObjects(unittest.TestCase):
    def __init__(self, methodName='runTest'):  
        super().__init__(methodName)  
        self.in_folder = get_datafolder('sample_data')
        from molass.DataObjects import SecSaxsData as SSD
        self.ssd = SSD(self.in_folder)

    def test_constructor(self):
        self.assertTrue(hasattr(self, 'ssd'))

    def test_get_xr_icurve(self):
        ssd = self.ssd
        xr_curve = ssd.xr.get_icurve()
        self.assertEqual(len(xr_curve.x), ssd.xr_data.M.shape[1])
        xr_baseline = ssd.xr.get_ibaseline()
        self.assertEqual(len(xr_baseline.x), len(xr_curve.x))
        sub_curve = xr_curve - xr_baseline
        add_curve = sub_curve + xr_baseline
        self.assertAlmostEqual(np.max(np.abs(xr_curve.y - add_curve.y)), 0)

    def test_get_xr_jcurve(self):
        ssd = self.ssd
        icurve = ssd.get_xr_icurve()
        j = np.argmax(icurve.y)
        icurve = ssd.get_xr_jcurve(j)
        self.assertEqual(len(icurve.x), ssd.xr_data.M.shape[0])

    def test_get_uv_icurve(self):
        ssd = self.ssd
        uv_curve = ssd.uv.get_icurve()
        self.assertEqual(len(uv_curve.x), ssd.uv_data.M.shape[1])
        uv_baseline = ssd.get_uv_ibaseline()
        self.assertEqual(len(uv_baseline.x), len(uv_curve.x))
        sub_curve = uv_curve - uv_baseline
        add_curve = sub_curve + uv_baseline
        self.assertAlmostEqual(np.max(np.abs(uv_curve.y - add_curve.y)), 0)

    def test_get_uv_jcurve(self):
        ssd = self.ssd
        icurve = ssd.uv.get_baseline2d_icurve()
        j = np.argmax(icurve.y)
        jcurve = ssd.get_uv_jcurve(j)
        self.assertEqual(len(jcurve.x), ssd.uv_data.M.shape[0])

    def test_copy(self):
        ssd = self.ssd.copy()
        self.assertEqual(ssd.xr_data.M.shape, self.ssd.xr_data.M.shape)
        self.assertEqual(ssd.uv_data.M.shape, self.ssd.uv_data.M.shape)
        print("ssd.uvM.shape=", ssd.uv_data.M.shape)
        ssd = self.ssd.copy(xr_slices=[slice(100,500), slice(50,100)],
                            uv_slices=[slice(100,200), slice(300,600)])
        self.assertEqual(ssd.xr_data.M.shape, (400,50))
        self.assertEqual(ssd.uv_data.M.shape, (100,300))

if __name__ == '__main__':
    unittest.main()