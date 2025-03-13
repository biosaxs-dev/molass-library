"""
    Peaks.Similarity.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.optimize import minimize

class PeakSimilarity:
    def __init__(self, x, y1, y2, try_both_signs=False):
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
        return self.results[0]
    
    def get_stdratio(self):
        result = self.get_minimizer_result()
        std = self.objective(result.x, return_std=True)
        return abs(std/result.x[0])