"""
    test DenssDetector
"""
import sys
sys.path.insert(0, r'D:\Github\molass-library')
sys.path.insert(0, r'D:\Github\molass-legacy')
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used

def test_01_sphere():
    from molass.SAXS.DenssDetector import get_denss_detector
    import numpy as np
    from molass.Shapes import Sphere
    from molass.DensitySpace import VoxelSpace
    from molass.SAXS.Simulator import compute_saxs

    N = 64
    sphere = Sphere(radius=20.0)
    space = VoxelSpace(N, sphere)

    q = np.linspace(0.005, 0.7, 100)
    denss_detector = get_denss_detector(q, space.rho, debug=False)
    
    print("DenssDetector:", denss_detector)

if __name__ == "__main__":
    test_01_sphere()