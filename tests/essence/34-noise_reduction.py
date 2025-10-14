"""
Noise reduction tests with controlled execution order.
Requires: pip install pytest-order
"""

import pytest
from molass.Testing import control_matplotlib_plot

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_def_plot_single_component_data():
    import numpy as np
    import matplotlib.pyplot as plt
    from molass.SAXS.Models.Simple import guinier_porod
    from molass.SEC.Models.Simple import gaussian
    from molass.LowRank.LowRankInfo import get_denoised_data
    global plot_single_component_data

    x = np.arange(300)
    q = np.linspace(0.005, 0.5, 400)

    def plot_single_component_data(scatter_params, elution_params, noise=None):
        G, Rg, d = scatter_params
        h, m, s = elution_params
        fig = plt.figure(figsize=(15,8))
        ax1 = fig.add_subplot(231)
        ax2 = fig.add_subplot(232)
        ax3 = fig.add_subplot(233, projection='3d')
        ax4 = fig.add_subplot(234)
        ax5 = fig.add_subplot(235)
        ax6 = fig.add_subplot(236, projection='3d')

        I, q1 = guinier_porod(q, G, Rg, d, return_also_q1=True)
        # ax1.set_yscale('log')
        for ax in [ax1, ax4]:
            ax.set_title(f"Scattering Curve")
            ax.plot(q, I, label='True $P$')
            ax.axvline(q1, linestyle=':', color="green", label='Guinier-Porod $Q_1$')

        y = gaussian(x, h, m, s)
        for ax in [ax2, ax5]:
            ax.set_title("Elution Curve")
            ax.plot(x, y, label='True $C$')
            ax.legend()

        P = I.reshape((len(q),1))   # make it a matrix
        C = y.reshape((1,len(x)))   # make it a matrix
        M = P @ C                   # matrix multiplication
        if noise is not None:
            M += noise * np.random.randn(*M.shape)
        xx, qq = np.meshgrid(x, q)
        ax3.set_title("3D View: $M_{noisy}$")
        ax3.plot_surface(qq, xx, M)

        Cinv = np.linalg.pinv(C)
        P_ = M @ Cinv
        ax1.plot(q, P_, linestyle=':', color="red", label='$P_{noisy}$')

        D = get_denoised_data(M, rank=1)
        ax6.set_title("3D View: $M_{denoised}$")
        ax6.plot_surface(qq, xx, D)

        Pd = D @ Cinv
        ax4.plot(q, Pd, linestyle=':', color="red", label='$P_{denoised}$')

        for ax in [ax1, ax4]:
            ax.legend()

        fig.tight_layout()

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_plot_single_component_data():
    plot_single_component_data((1, 35, 3), (1, 150, 30), noise=0.1)