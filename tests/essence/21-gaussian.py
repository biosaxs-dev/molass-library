"""
Gaussian curve tests with controlled execution order.
Requires: pip install pytest-order
"""

import numpy as np

import pytest
from molass.Testing import control_matplotlib_plot

@pytest.mark.order(1)
def test_001_gaussian():
    global gaussian
    def gaussian(x, A=1.0, mu=0.0, sigma=1.0):
        return A * np.exp(-((x - mu)**2/(2*sigma**2)))

@pytest.mark.order(2)
def test_002_mean_std():
    x = np.linspace(-5, 5, 100)
    y = gaussian(x, A=1.0, mu=0.0, sigma=1.0)
    w = np.sum(y)
    mean = np.sum(x * y) / w
    variance = np.sum((x - mean) ** 2 * y) / w
    expected = (0.0, 1.0)
    assert (mean, np.sqrt(variance)) == pytest.approx(expected, abs=1e-2)

@pytest.mark.order(3)
@control_matplotlib_plot 
def test_003_def_plot_gaussian():
    import matplotlib.pyplot as plt
    global plot_gaussian
    def plot_gaussian(x, A=1.0, mu=0.0, sigma=1.0):    
        y = gaussian(x, A, mu, sigma)
        
        w = np.sum(y)
        mean = np.sum(x * y) / w
        variance = np.sum((x - mean) ** 2 * y) / w
        std = np.sqrt(variance)
        print("Mean:", mean)
        print("Variance:", variance)
        print("Standard Deviation:", std)

        plt.figure(figsize=(8, 4))
        plt.plot(x, y, label=f'Gaussian: A={A}, μ={mu}, σ={sigma}')
        plt.axvline(mean, color='r', linestyle='--', label='Mean')
        plt.axvline(mean + std, color='g', linestyle='--', label='Std Dev')
        plt.axvline(mean - std, color='g', linestyle='--')
        plt.title('Gaussian Function')
        plt.xlabel('x')
        plt.ylabel('f(x)')
        plt.grid()
        plt.legend()
        plt.show()

@pytest.mark.order(4)
@control_matplotlib_plot
def test_004_plot_gaussian():
    x = np.arange(300)
    plot_gaussian(x, A=1.0, mu=150.0, sigma=30.0)
