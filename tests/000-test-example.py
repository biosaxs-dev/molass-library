import sys
import os
testdir = os.path.dirname(__file__)
libhome = os.path.dirname(testdir)
sys.path.insert(0, libhome)
import unittest

class TestDataObjects(unittest.TestCase):
    def __init__(self, methodName='runTest'):  
        super().__init__(methodName)  

    def test_example(self):
        from molass import example
        ret = example()
        self.assertEqual(ret, None)

if __name__ == '__main__':
    unittest.main()