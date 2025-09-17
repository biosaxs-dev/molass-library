"""
    test DenssTools
"""
import sys
sys.path.insert(0, r'D:\Github\molass-library')
sys.path.insert(0, r'D:\Github\molass-legacy')
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
import matplotlib.pyplot as plt

def test_01_sphere():
    from molass.Shapes import Sphere
    from molass.DensitySpace import VoxelSpace

    sphere = Sphere(radius=10.0)
    space = VoxelSpace(32, sphere)
    space.plot_as_dots()
    plt.show()

def test_02_ellipsoid():
    from molass.Shapes import Ellipsoid
    from molass.DensitySpace import VoxelSpace

    ellipsoid = Ellipsoid(a=10.0, b=5.0, c=15.0)
    space = VoxelSpace(32, ellipsoid)
    space.plot_as_dots()
    plt.show()

if __name__ == "__main__":
    # test_01_sphere()
    test_02_ellipsoid()