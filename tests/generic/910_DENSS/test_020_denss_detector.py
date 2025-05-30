"""
    test DenssDetector
"""
import sys
sys.path.insert(0, r'D:\Github\molass-library')
sys.path.insert(0, r'D:\Github\molass-legacy')
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used

def test_01_sphere():
    from molass.SAXS.Simulator import ElectronDensitySpace
    from molass.SAXS.DenssDetector import get_denss_detector
    import numpy as np

    N = 64
    eds = ElectronDensitySpace(N=N)
    x, y, z = eds.get_meshgrid()
    shape_condition = (x - N//2)**2 + (y - N//2)**2 + (z - N//2)**2 < (N//4)**2
    rho = np.zeros((N, N, N))
    rho[shape_condition] = 1

    q = np.linspace(0.005, 0.7, 100)
    denss_detector = get_denss_detector(q, rho, debug=False)
    
    print("DenssDetector:", denss_detector)

if __name__ == "__main__":
    test_01_sphere()