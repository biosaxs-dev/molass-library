"""
    Stats.Moment.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import numpy as np

def compute_meanstd(x, y):
    """Compute the mean and standard deviation of a distribution defined by x and y.

    Parameters
    ----------
    x : array-like
        The x-values of the distribution.
    y : array-like
        The y-values of the distribution.

    Returns
    -------
    M1 : float
        The mean of the distribution.
    std : float
        The standard deviation of the distribution.
    """
    W = np.sum(y)
    M1 = np.sum(x*y)/W              # raw moment
    M2 = np.sum(y*(x-M1)**2)/W      # central moment
    return M1, np.sqrt(M2)

class Moment:
    """A class to represent the moment of a distribution defined by x and y.
    Attributes
    ----------
    x : array-like
        The x-values of the distribution.
    y : array-like
        The y-values of the distribution.
    y_ : array-like or None
        The processed y-values of the distribution. If None, it has not been computed yet.
    M : float or None
        The mean of the distribution. If None, it has not been computed yet.
    std : float or None
        The standard deviation of the distribution. If None, it has not been computed yet.
    lpm_percent : float or None
        The estimated percentage of low-q plateau in the distribution. If None, it has not been computed yet.
    """
    def __init__(self, x, y):
        """Initialize the Moment object.
        Parameters
        ----------
        x : array-like
            The x-values of the distribution.
        y : array-like
            The y-values of the distribution.
        """
        self.x = x
        self.y = y
        self.y_ = None
        self.M = None       # to avoid repeated computation in case with multiple references
        self.std = None
        self.lpm_percent = None
    
    def get_y_(self, **kwargs):
        """Get the processed y-values of the distribution.
            If y_ is None, it will be computed using the provided processing function.

        Parameters
        ----------
        **kwargs : keyword arguments
            Additional keyword arguments to pass to the processing function.

        Returns
        -------
        y_ : array-like
            The processed y-values of the distribution.
        """
        if self.y_ is None:
            y_ = self.y.copy()
            y_[y_ < 0] = 0  # negative values are usually inappropriate for weights
            self.y_ = y_
        return self.y_
    
    def debug_plot(self, ax):
        """Plot the original and processed y-values for debugging purposes.
        
        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The axes to plot on.
        """
        y_ = self.get_y_()
        ax.plot(self.x, self.y, label='y')
        ax.plot(self.x, y_, ":", label='y_')
        ax.legend()
 
    def get_meanstd(self):
        """Get the mean and standard deviation of the distribution.
            If M and std are None, they will be computed using the processed y-values.

        Returns
        -------
        M : float
            The mean of the distribution.
        std : float
            The standard deviation of the distribution.
        """
        if self.y_ is None:
            y_ = self.get_y_()
            self.M, self.std = compute_meanstd(self.x, y_)
        return self.M, self.std
    
    def is_in_nsigma(self, n, px):
        """Check if a given x-value is within n standard deviations from the mean.
        
        Parameters
        ----------
        n : float
            The number of standard deviations.
        px : float
            The x-value to check.

        Returns
        -------
        bool
            True if px is within n standard deviations from the mean, False otherwise.
        """
        M, std = self.get_meanstd()
        return M - n*std < px and px < M + n*std
    
    def get_nsigma_points(self, n):
        """Get the indices of the x-values that are within n standard deviations from the mean.

        Parameters
        ----------
        n : float
            The number of standard deviations.

        Returns
        -------
        (i, j) : tuple of int
            The indices of the first and last x-values within n standard deviations from the mean.
            If no such points exist, returns (None, None).
        """
        M, std = self.get_meanstd()
        try:
            wanted_range = np.logical_and(M - n*std < self.x, self.x < M + n*std)
            i, j = np.where(wanted_range)[0][[0,-1]]
            return i, j
        except Exception as e:
            print(f"Error in get_nsigma_points: {e}")
            import matplotlib.pyplot as plt
            print("M, std, n, y_:", M, std, n, self.y_)
            plt.plot(self.x, self.y, label='y')
            plt.plot(self.x, self.y_, label='y_')
            plt.axvline(M - n*std, color='r', linestyle='--', label='Lower Bound')
            plt.axvline(M + n*std, color='r', linestyle='--', label='Upper Bound')
            plt.legend()
            plt.show()
            return None, None

    def get_lpm_percent(self, debug=True):
        """Estimate the percentage of low-q plateau in the distribution.
        
        Parameters
        ----------
        debug : bool, optional
            If True, enables debug mode for more verbose output, by default True.

        Returns
        -------
        lpm_percent : float
            The estimated percentage of low-q plateau in the distribution.
        """
        if self.lpm_percent is None or debug:
            if debug:
                from importlib import reload
                import molass.Baseline.LpmBaseline
                reload(molass.Baseline.LpmBaseline)
            from molass.Baseline.LpmBaseline import estimate_lpm_percent
            self.lpm_percent = estimate_lpm_percent(self)
        return self.lpm_percent