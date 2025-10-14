"""
PlotUtils.TwinAxesUtils.py
"""
import numpy as np
from scipy.optimize import minimize

VERY_SMALL_NUMBER = 1e-10

def align_zero_y(ax1, axt, debug=False):
    """
    task: simpler implementation
    """
    # Get current limits
    ymin1, ymax1 = ax1.get_ylim()
    ymin2, ymax2 = axt.get_ylim()

    # Set the same y-limits for both axes
    original_scale_ratio = (ymax1 - ymin1) / (ymax2 - ymin2)
 
    init_params = [ymin1, ymin2] 

    def objective(params):
        ymin1_, ymin2_ = params
        p1 = (0 - ymin1_) / (ymax1 - ymin1_)
        p2 = (0 - ymin2_) / (ymax2 - ymin2_)
        scale_ratio = (ymax1 - ymin1_) / (ymax2 - ymin2_)
        return (np.log10(max(VERY_SMALL_NUMBER, (p1 - p2)**2))
                # + np.log10(max(VERY_SMALL_NUMBER, (scale_ratio - original_scale_ratio)**2))
                + np.log10(max(VERY_SMALL_NUMBER, (ymin1_- ymin1)**2))
                )
    
    result = minimize(objective, init_params, method='Nelder-Mead')
    ymin1_, ymin2_ = result.x
    ax1.set_ylim(ymin1_, ymax1)
    axt.set_ylim(ymin2_, ymax2)

    if debug:
        print("Optimized Y-limits:")
        print(ymin1, ymin2)
        print(ymin1_, ymin2_)
        print("Objective function value:", result.fun)