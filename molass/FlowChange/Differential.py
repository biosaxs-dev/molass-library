"""
FlowChange.Differential.py
"""
from scipy.optimize import minimize

LIKELY_RATIO_LIMIT = 0.7    # > 0.65 for 20210323_1 (likely), < 1.00 for 20171203 (not likely)

def islike_differential(curve1, curve2, debug=False):
    """
    Check if curve2 is like a differential change of curve1.
    
    Args:
        curve1 (Curve): The first curve.
        curve2 (Curve): The second curve.

    Returns:
        bool: True if the flow change is like a differential, False otherwise.
    """
    if debug:
        from time import time
        start_time = time()

    x = curve1.x
    diff_spline = curve1.get_diff_spline()
    dy = diff_spline(x)
    
    def objective_function(params):
        """
        Objective function to minimize the difference between dy and curve2.y.
        
        Args:
            params (list): Parameters to optimize.

        Returns:
            float: The sum of squared differences.
        """
        return ((dy*params[0] - curve2.y) ** 2).sum()

    init_scale = max(dy)/curve2.get_max_y()
    result = minimize(objective_function, [init_scale], method='Nelder-Mead')
    fit_ratio = result.fun / objective_function([0])
    if debug:
        import matplotlib.pyplot as plt
        print(f"Time taken: {time() - start_time:.6f} seconds")     # it seems to take less than 0.02 seconds
        print(f"Initial scale: {init_scale}, Optimized scale: {result.x[0]}, Success: {result.success}")
        print(f"Fit ratio: {fit_ratio}")
        fig, ax = plt.subplots()
        ax.plot(x, dy * result.x[0], label='Scaled Differential')
        ax.plot(x, curve2.y, label='Curve2')
        ax.legend()
        fig.tight_layout()
        plt.show()

    return fit_ratio < LIKELY_RATIO_LIMIT