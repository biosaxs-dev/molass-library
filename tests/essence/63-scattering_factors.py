"""
Form and structure factors tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
from molass.Testing import control_matplotlib_plot

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_homogeneous_sphere():
    from molass import get_version
    assert get_version() >= '0.5.0', "This tutorial requires molass version 0.5.0 or higher."
    import numpy as np
    import matplotlib.pyplot as plt
    from molass.Shapes import Sphere
    from molass.DensitySpace import VoxelSpace
    from molass.SAXS.Models.Formfactors import homogeneous_sphere

    q = np.linspace(0.005, 0.7, 100)
    R = 30

    I = homogeneous_sphere(q, R)

    sphere = Sphere(radius=10)
    space = VoxelSpace(64, sphere)

    fig = plt.figure(figsize=(12, 5))
    fig.suptitle('Form factor of a Homogeneous Sphere')
    ax1 = fig.add_subplot(121, projection='3d')
    ax1.set_title('Electron density')
    space.plot_as_dots(ax1)

    ax2 = fig.add_subplot(122)
    ax2.set_title('SAXS intensity')
    ax2.set_yscale('log')
    ax2.plot(q, I, label='Analitical formula')
    ax2.legend()
    ax2.set_xlabel('q (1/Å)')