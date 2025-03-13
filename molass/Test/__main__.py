"""
    cf. https://realpython.com/python-unittest/
"""
import sys
import os
testdir = os.path.dirname(__file__)
libhome = os.path.dirname(os.path.dirname(testdir))
sys.path.insert(0, libhome)

import unittest

from molass.Test.TestDataObjects import TestDataObjects
from molass.Test.TestDataUtils import TestDataUtils
from molass.Test.TestPeaklike import TestPeaklike
from molass.Test.TestFlowChange import TestFlowChange

if __name__ == '__main__':
    unittest.main()