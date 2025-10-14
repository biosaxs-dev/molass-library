"""
Linear transformation tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
from molass.Testing import control_matplotlib_plot

@pytest.mark.order(1)
def test_001_def_plot_multiple_component_data_with_svd():
    import numpy as np
    import matplotlib.pyplot as plt
    from molass.SAXS.Models.Simple import guinier_porod
    from molass.SEC.Models.Simple import gaussian
    global plot_multiple_component_data_with_svd

    x = np.arange(300)
    q = np.linspace(0.005, 0.5, 400)
    
    def plot_multiple_component_data_with_svd(rgs, scattering_params, elution_params, use_matrices=False, view=None):
        fig = plt.figure(figsize=(15,5))
        ax1 = fig.add_subplot(131)
        ax2 = fig.add_subplot(132)
        ax3 = fig.add_subplot(133)
        
        fig.suptitle(r"Observation of Singular Value Decomposition", fontsize=16)

        w_list = []
        for i, (G, Rg, d) in enumerate(scattering_params):
            I, q1 = guinier_porod(q, G, Rg, d, return_also_q1=True)
            w_list.append(I)

        y_list = []
        ax1.set_title("Elution Curves in C", fontsize=14)
        ax1.set_xlabel("Frames")
        ax1.set_ylabel("Concentration")
        for i, (h, m, s) in enumerate(elution_params):
            y = gaussian(x, h, m, s)
            y_list.append(y)
            ax1.plot(x, y, label='component-%d: $R_g=%.3g$' % (i+1, rgs[i]))
        ty = np.sum(y_list, axis=0)
        ax1.plot(x, ty, ':', color='red', label='total')
        ax1.legend()

        P = np.array(w_list).T
        C = np.array(y_list)
        M = P @ C

        U, s, VT = np.linalg.svd(M)
        ax2.plot(s[0:10], 'o', color='gray', alpha=0.5, label='Singular Values')
        print("Top ten Singular Values:", s[0:10])
        s_ = s[s > 0.001 * s[0]]
        ax2.plot(s_, 'o', color='red', label='Major Singular Values')
        ax2.set_title(r"Singular Values of $M = P \cdot C$", fontsize=14)
        ax2.set_xlabel("Index")
        ax2.set_ylabel("Value")
        ax2.legend()

        ax3.set_title("$V^T$ Major Components")
        for i in range(len(s_)):
            ax3.plot(x, VT[i], label='component-%d' % (i+1))
        ax3.legend()

        fig.tight_layout()
        fig.subplots_adjust(right=0.95)

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_plot_multiple_component_data_with_svd():
    rgs = (35, 32, 23)
    scattering_params = [(1, rgs[0], 2), (1, rgs[1], 3), (1, rgs[2], 4)]
    elution_params = [(1, 100, 12), (0.3, 125, 16), (0.5, 200, 16)]
    plot_multiple_component_data_with_svd(rgs, scattering_params, elution_params, use_matrices=True, view=(-15, 15))