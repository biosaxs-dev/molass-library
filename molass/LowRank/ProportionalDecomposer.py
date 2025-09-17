"""
LowRank.ProportionalDecomposer.py

This module contains the functions to decompose a curve according to
specified peak area proportions.
"""
import numpy as np
from bisect import bisect_right
from scipy.optimize import minimize, basinhopping
from molass_legacy.KekLib.SciPyCookbook import smooth
from molass.SEC.Models.Simple import egh, e0
from molass.Stats.Moment import compute_meanstd

SQRT_PI_8 = np.sqrt(np.pi/8)

def compute_egh_area_fast(h, sigma, tau):
    tau_ = abs(tau)
    th = np.arctan2(tau_, sigma)
    return h * (sigma * SQRT_PI_8 + tau_)*e0(th)

IGNORE_PROP = 0.02
BASIN_HOPPING = False

def decompose_icurve_proportionally(x, y, decompargs, **kwargs):
    debug = kwargs.get('debug', False)
    proportions = decompargs.get('proportions', [])
    print("proportions=", proportions)
    n = len(proportions)
    if n == 0:
        raise ValueError("No peak proportions specified.")
    tau_limit = decompargs.get('tau_limit', 0.6)
    max_sigma = decompargs.get('max_sigma', 17)

    proportions = np.asarray(proportions)
    proportions = proportions/np.sum(proportions)

    sy = smooth(y)
    sy[sy < 0] = 0
    integ_y = np.cumsum(sy)
    integ_prop = np.cumsum(proportions)
    work_proportions = np.concatenate([[IGNORE_PROP], integ_prop[0:-1], [1 -IGNORE_PROP], [1]])
    integ_propy = work_proportions*integ_y[-1]

    div_points = []
    for px in integ_propy[:-1]:
        i = bisect_right(integ_y, px)
        div_points.append(i)

    mid_pointsy = (integ_propy[0:-1] + integ_propy[1:])/2
    mid_points = []
    for px in mid_pointsy[:-1]:
        i = bisect_right(integ_y, px)
        mid_points.append(i)

    params_list = []
    for i in range(len(div_points)-1):
        start = div_points[i]
        stop = div_points[i+1]
        m, s = compute_meanstd(x[start:stop], sy[start:stop])
        params_list.append((sy[mid_points[i]], m, s, 0))

    init_params = np.array(params_list)

    bounds = []
    for h, m, s, t in init_params:
        bounds.append((h*0.5, h*1.5))
        bounds.append((m - s*0.2, m + s*0.2))
        bounds.append((s*0.9, s*1.1))
        bounds.append((-s, s))

    total_area = np.sum(sy)
    allow = 0.1*total_area
    shape = init_params.shape
    dev_weights = decompargs.get('dev_weights', (1,5))

    def fit_func(p, ax=None):
        area_list = []
        params = p.reshape(shape)
        cy_list = []
        tau_penalty = 0
        for h, m, s, t in params:
            cy = egh(x, h, m, s, t)
            cy_list.append(cy)
            area = compute_egh_area_fast(h, s, t)
            area_list.append(area)
            tau_penalty += max(0, t/s - tau_limit)**2
        tau_penalty *= 1000
        ty = np.sum(cy_list, axis=0)
        order_penalty = min(0, np.min(np.diff(params[:,1])))*1000
        area_list = np.asarray(area_list)
        total = np.sum(area_list)
        total_penalty = 1000*min(0, allow - abs(total - total_area))**2
        area_list = area_list/total
        prop_dev = np.sum((area_list - proportions)**2)
        fit_dev = np.sum((ty - y)**2)
        v = np.log(prop_dev)*dev_weights[0] + np.log(fit_dev)*dev_weights[1] + total_penalty + order_penalty + tau_penalty
        # v = np.log(fit_dev)+ total_penalty + order_penalty + tau_penalty
        if ax is not None:
            print("area_list=", area_list)
            print("total_penalty=", total_penalty)
            print("tau_penalty=", tau_penalty)
            ax.plot(x, y)
            cy_list = []
            for h, m, s, t in params:
                cy = egh(x, h, m, s, t)
                ax.plot(x, cy, ":")
                cy_list.append(cy)
            ty = np.sum(cy_list, axis=0)
            ax.plot(x, ty, ":", color='red')    
        return v

    use_basinhopping = decompargs.get('basinhopping', BASIN_HOPPING)
    if BASIN_HOPPING or use_basinhopping:
        print("Using basinhopping with dev_weights=%s" % str(dev_weights))
        minimizer_kwargs = dict(method="Nelder-Mead", bounds=bounds)
        res= basinhopping(fit_func, init_params.flatten(), minimizer_kwargs=minimizer_kwargs)
    else:
        res = minimize(fit_func, init_params.flatten(), method='Nelder-Mead', bounds=bounds)

    ret_params = res.x.reshape(shape)

    if debug:
        def debug_plot(params):
            import matplotlib.pyplot as plt
            print("integ_prop=", integ_prop)
            print("integ_propy=", integ_propy)
            print("mid_pointsy=", mid_pointsy)
            print("work_proportions=", work_proportions)
            fig, (ax1,ax2,ax3) = plt.subplots(ncols=3, figsize=(18,5))
            fig.suptitle("decompose_icurve_proportionally debug")
            ax1.plot(x, y)
            ax1.plot(x, sy, ":")
            axt = ax1.twinx()
            axt.plot(x, integ_y, ":", color='red')
            for i in div_points:
                ax1.axvline(x[i], color='yellow')
            for i in mid_points:
                ax1.axvline(x[i], color='green', alpha=0.5)
            ax2.plot(x, y)
            cy_list = []
            for h, m, s, t in params:
                cy = egh(x, h, m, s, t)
                cy_list.append(cy)
                ax2.plot(x, cy, ":")
            ty = np.sum(cy_list, axis=0)
            ax2.plot(x, ty, ":", color='red')

            fit_func(res.x, ax=ax3)

            fig.tight_layout()
            plt.show()
        debug_plot(init_params)
        debug_plot(ret_params)

    return ret_params




