"""
Sphere scattering tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
from molass.Testing import configure_for_test

@pytest.mark.order(1)
@configure_for_test
def test_001_homogeneous_sphere():
    from molass import get_version
    assert get_version() >= '0.6.0', 'Please update molass to the latest version'
    import numpy as np
    import matplotlib.pyplot as plt
    from molass.SAXS.Models.Formfactors import homogeneous_sphere

    q = np.linspace(0.005, 0.7, 100)
    R = 30

    I = homogeneous_sphere(q, R)**2
    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10, 5))
    ax2.set_yscale('log')
    for ax in ax1, ax2:
        ax.plot(q, I, label='homogeneous sphere')
