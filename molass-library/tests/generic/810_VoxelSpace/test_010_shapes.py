"""
    test DensitySpace with different Shapes
"""
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
import matplotlib.pyplot as plt
from molass.Testing import control_matplotlib_plot

@control_matplotlib_plot
def test_01_sphere():
    from molass.Shapes import Sphere
    from molass.DensitySpace import VoxelSpace

    sphere = Sphere(radius=10.0)
    space = VoxelSpace(32, sphere)
    space.plot_as_dots()
    plt.show()

@control_matplotlib_plot
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