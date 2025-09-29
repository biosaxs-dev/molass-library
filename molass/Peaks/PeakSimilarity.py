"""
    Peaks.Similarity.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.optimize import minimize

class PeakSimilarity:
    """A class to evaluate the similarity between two peaks by fitting one peak to another.
    It uses a scaling factor and a linear baseline (slope and intercept) to fit the first peak to the second peak.

    Attributes
    ----------
    objective : function
        The objective function to minimize, which computes the difference between the scaled and shifted first peak and the second peak.
    results : list of OptimizeResult
        The results of the optimization for different initial conditions.
    """
    def __init__(self, x, y1, y2, try_both_signs=False):
        """
        Initialize the PeakSimilarity object.

        Parameters
        ----------
        x : np.ndarray
            The x values of the peaks.
        y1 : np.ndarray
            The y values of the first peak to be fitted.
        y2 : np.ndarray
            The y values of the second peak to which the first peak is fitted.
        try_both_signs : bool, optional
            If True, try both positive and negative scaling factors for the first peak.
            Default is False.
        """
        max_y1 = np.max(y1)
        height = (np.max(y2) - np.min(y2))*0.8
        scale = height/max_y1

        def objective(p, return_std=False):
            scale, slope, intercept = p
            diff = y2 - (x*slope + intercept) - y1*scale
            if return_std:
                # this will be used for std/scale ratio
                return np.std(diff)
            else:
                # this is better for optimization
                return np.sum(diff**2)

        self.objective = objective

        if try_both_signs:
            results = []
            for sign in (1, -1):
                method = None
                res = minimize(objective, (sign*scale, 0, 0))
                results.append(res)
            results = sorted(results, key=lambda x: x.fun)
        else:
            res = minimize(objective, (scale, 0, 0))
            results = [res]

        self.results = results

    def get_minimizer_result(self):
        """Get the best minimizer result.
        Returns
        -------
        OptimizeResult
            The best result from the optimization.
        """
        return self.results[0]
    
    def get_stdratio(self):
        """Get the standard deviation to scale ratio from the best minimizer result.
        Returns
        -------
        float
            The standard deviation to scale ratio.
        """
        result = self.get_minimizer_result()
        std = self.objective(result.x, return_std=True)
        return abs(std/result.x[0])