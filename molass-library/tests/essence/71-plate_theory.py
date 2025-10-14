"""
Plate theory tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
from molass.Testing import control_matplotlib_plot

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_variance_approximation():
    import numpy as np
    import matplotlib.pyplot as plt
    from molass.SEC.Models.Simple import egh, e1
    from molass.Stats.Moment import compute_meanstd
    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(12, 5))
    x = np.arange(300)

    vars1 = []
    vars2 = []
    vars3 = []

    tau_list = [0, 5, 10, 15]
    for tau in tau_list:
        y = egh(x, 1, 100, 20, tau)
        ax1.plot(x, y, label=f'tau={tau}')
        mean, std = compute_meanstd(x, y)
        vars1.append(std**2)
        vars2.append(20**2 + tau**2 - 20*tau/5.577)
        theta = np.arctan(tau/20)
        vars3.append((20**2 + 20*tau + tau**2)*e1(theta))

    ax1.set_title('EGH with different tau')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Concentration')
    ax1.legend()

    ax2.plot(tau_list, vars1, 'o-', label='Numerically computed')
    ax2.plot(tau_list, vars2, 's--', label='Approx. Formula')
    ax2.plot(tau_list, vars3, 'x--', label='Derived Formula')
    ax2.set_title(r'Accuracy of Variance Approximation')
    ax2.set_xlabel('tau')
    ax2.set_ylabel(r'Variance ($\bar{M_2}$)')
    ax2.set_xticks(tau_list)
    ax2.set_xticklabels(tau_list)
    ax2.legend()
    fig.tight_layout()