"""
EGH curve tests with controlled execution order.
Requires: pip install pytest-order
"""

import numpy as np
import matplotlib.pyplot as plt

import pytest
from molass.Testing import control_matplotlib_plot

@pytest.mark.order(1)
def test_001_def_plot_egh():
    import numpy as np
    global plot_egh
    def plot_egh(x, A=1.0, mu=0.0, sigma=1.0, tau=1.0):
        from molass.SEC.Models.Simple import egh
        y = egh(x, A, mu, sigma, tau)

        w = np.sum(y)
        mean = np.sum(x * y) / w
        variance = np.sum((x - mean) ** 2 * y) / w
        std = np.sqrt(variance)

        plt.plot(x, y)
        plt.axvline(mean, color='r', linestyle='--', label='Mean')
        plt.axvline(mean + std, color='g', linestyle='--', label='Std Dev')
        plt.axvline(mean - std, color='g', linestyle='--')
        plt.legend()
        plt.title('Exponential-Gaussian Hybrid Function')
        plt.xlabel('x')
        plt.ylabel('f(x)')
        plt.grid()
        plt.show()

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_plot_egh():
    global x
    x = np.arange(300)
    plot_egh(x, A=1.0, mu=150.0, sigma=30.0, tau=0)

@pytest.mark.order(3)
@control_matplotlib_plot 
def test_003_def_plot_egh_curves():
    global plot_egh_curves
    def plot_egh_curves(x, params):
        from molass.SEC.Models.Simple import egh, egh_std
        for k, param in enumerate(params):
            A = param['A']
            mu = param['mu']
            sigma = param['sigma']
            tau = param['tau']
            y = egh(x, A, mu, sigma, tau)
            plt.plot(x, y, label=f"A={A}, mu={mu}, sigma={sigma}, tau={tau}")
            if k == 1:
                w = np.sum(y)
                mean = np.sum(x * y) / w
                variance = np.sum((x - mean) ** 2 * y) / w
                std = np.sqrt(variance)
                plt.axvline(mean, color='r', linestyle='--', label='Mean')
                plt.axvline(mean + std, color='g', linestyle='--', label='Std Dev')
                plt.axvline(mean - std, color='g', linestyle='--')
                print("std=", std)
                print("egh_std=", egh_std(sigma, tau)) # std and egh_std should be nearly equal
        plt.title('Exponential-Gaussian Hybrid Functions')
        plt.xlabel('x')
        plt.ylabel('f(x)')
        plt.grid()
        plt.legend()
        plt.show()

@pytest.mark.order(4)
@control_matplotlib_plot
def test_004_plot_egh_curves():
    plot_egh_curves(x, [
        {'A': 1.0, 'mu': 150.0, 'sigma': 30.0, 'tau': 0},
        {'A': 1.0, 'mu': 150.0, 'sigma': 30.0, 'tau': 20},
    ])

@pytest.mark.order(5)
@control_matplotlib_plot
def test_005_plot_egh_curves_negative_tau():
    plot_egh_curves(x, [
        {'A': 1.0, 'mu': 150.0, 'sigma': 30.0, 'tau': 0},
        {'A': 1.0, 'mu': 150.0, 'sigma': 30.0, 'tau': -20},
    ])
