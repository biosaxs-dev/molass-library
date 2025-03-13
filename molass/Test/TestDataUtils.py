"""
    Test.TestDataUtils.py

    cf. https://realpython.com/python-unittest/
"""
import sys
import os
testdir = os.path.dirname(__file__)
libhome = os.path.dirname(os.path.dirname(testdir))
sys.path.insert(0, libhome)

import unittest
from molass.Test.TestSettings import get_datafolder

class TestDataUtils(unittest.TestCase):
    def __init__(self, methodName='runTest'):  
        super().__init__(methodName)
        self.root_folder = get_datafolder()
        self.in_folder = get_datafolder('sample_data')

    def test_load_uv(self):
        from molass.DataUtils.UvLoader import load_uv
        uvM, wvector = load_uv(self.in_folder)
        self.assertEqual(uvM.shape, (318,711))
        self.assertEqual(len(wvector), 318)

        uvfile = os.path.join(self.in_folder, 'SAMPLE_UV280_01.txt')
        uvM, wvector = load_uv(uvfile)
        self.assertEqual(uvM.shape, (318,711))
        self.assertEqual(len(wvector), 318)

    def test_walk_folders(self):
        from molass.DataUtils.FolderWalker import walk_folders
        folders = []
        for folder in walk_folders(self.root_folder):
            folders.append(folder)
            if len(folders) >= 10:
                break
        self.assertEqual(len(folders), 10)

if __name__ == '__main__':
    unittest.main()