"""
    Baseline.UvDiffEffect.py
"""
import numpy as np
from molass.DataObjects.Curve import Curve

STDRATIO_UPPER_LIMIT = 0.01

def create_diff_spline(icurve):
    from molass_legacy.SerialAnalyzer.OptimalSmoothing import OptimalSmoothing
    x = icurve.x
    y = icurve.y
    m = np.argmax(y)
    max_y = y[m]
    min_y = np.percentile(y, 5)
    height = max_y - min_y
    smoothing = OptimalSmoothing(x, y, height, min_y)
    smoothing.compute_optimal_curves()
    return smoothing.d1

class UvDiffEffect(Curve):
    def __init__(self, ssd, params=None):
        from molass_legacy.Baseline.UvBaseSpline import compute_baseline_impl
        from molass_legacy.Baseline.Constants import SLOPE_SCALE
        icurve = ssd.uv.get_icurve()
        diff_spline = create_diff_spline(icurve)
        x = icurve.x
        temp_params = params.copy()
        temp_params[4:6] /= SLOPE_SCALE
        y = compute_baseline_impl(x, temp_params[0:7], diff_spline)
        super().__init__(x, y)
        self.params = params

def estimate_uvdiffeffect_params(curve1, curve2, fc_slice, diff_spline, pickat=None, debug=False, plot_info=None):
    if debug:
        from importlib import reload
        import molass.Peaks.PeakSimilarity
        reload(molass.Peaks.PeakSimilarity)
    from molass.Peaks.PeakSimilarity import PeakSimilarity

    x_ = curve2.x
    y_ = curve2.y
    i, j = fc_slice
    x = x_[i:j]
    y = y_[i:j]
    dy = diff_spline(x)
    
    ps = PeakSimilarity(x, dy, y, try_both_signs=True)
    dy_y_result = ps.get_minimizer_result()
    d_stdratio = ps.get_stdratio()
    # print("d_stdratio=", d_stdratio)

    if d_stdratio > STDRATIO_UPPER_LIMIT:
        ps = PeakSimilarity(x, curve1.y[i:j], y)
        p_stdratio = ps.get_stdratio()
        # print("p_stdratio=", p_stdratio)
    else:
        p_stdratio = np.nan

    adjusted_scale, slope, intercept = dy_y_result.x
    # baseline = dy*adjusted_scale + (x*slope + intercept)
    baseline = dy*adjusted_scale

    if debug or plot_info is not None:
        if plot_info is None:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
        else:
            fig, ax = plot_info
        ax.plot(curve1.x, curve1.y, alpha=0.5, label=r'$\lambda = 280$')
        axt = ax.twinx()
        axt.grid(False)
        if i is not None:
            axt.axvline(x_[i], color='yellow', label='flow change')
        if j is not None:
            axt.axvline(x_[j], ls=':', color='blue', label='flow change')
        axt.plot(x, dy, color='green', alpha=0.5, label=r'derivative at $\lambda=280$')
        cy = y - (x*slope + intercept)
        lambda_str = r'\geq 400' if pickat is None else "=%g" % pickat
        axt.plot(x, cy, color='red', alpha=0.5, label=r'data at $\lambda %s$' % lambda_str)
        axt.plot(x, dy*adjusted_scale, color='cyan', label='adjusted derivative')
        axt.plot(x_, y_, color='red', alpha=0.1)
        xmin, xmax = axt.get_xlim()
        ymin, ymax = axt.get_ylim()
        tx = xmin * 0.5 + xmax * 0.5
        ty = ymin * 0.5 + ymax * 0.5
        axt.text(tx, ty, "Fluctuation Scale=%.3g" % adjusted_scale,
                 ha='center', va='center',
                 alpha=0.3, fontsize=25)
        ax.legend(loc='upper left')
        avg_y = np.average(cy)
        ratio = (avg_y - ymin)/(ymax - ymin)
        vpos = 'upper' if ratio < 0.5 or j is not None else 'lower'
        axt.legend(loc='%s right' % vpos)
        fig.tight_layout()
        if plot_info is None:
            plt.show()

    return np.concatenate([dy_y_result.x, [d_stdratio, p_stdratio]]), dy, baseline

def compute_dfef_curve(x, dfef_params):
    y = np.zeros_like(x)
    return Curve(x, y)