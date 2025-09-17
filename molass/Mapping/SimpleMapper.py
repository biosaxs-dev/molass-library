"""
    Mapping.SimpleMapperpy
"""
import numpy as np
from scipy.stats import linregress
from sklearn.linear_model import LinearRegression
from molass.Mapping.MappingInfo import MappingInfo

ACCEPTABLE_COVERAGE_RATIO = 0.50    # < 0.57 for 20201005_1
RELIABLE_COVERAGE_RATIO = 0.60      # < 0.70 for 20201006_1, < 0.80 for 20200125_1, < 0.80 for 20200125_2
ACCEPTABLE_2SIGMA_RATIO = 0.05      #

def compute_mapping_coverage(x, y, slope, intercept, debug=False):
    """
    Check if the mapping covers the range of x and y.
    """
    y_ = x[[0,-1]]*slope + intercept
    ymin = max(y[0], y_[0])
    ymax = min(y[-1], y_[1])
    x_ = (ymin - intercept) / slope, (ymax - intercept) / slope
    xmin = max(x[0], x_[0])
    xmax = min(x[-1], x_[1])
    coverage_ratio = (xmax - xmin) / (x[-1] - x[0]) 
    return coverage_ratio

def estimate_slope_reliability(xr_curve, x, uv_curve, y, coverage_ratio, debug=False):
    """
    Estimate the reliability of the slope by comparing the peak ratios.
    """
    if coverage_ratio >= RELIABLE_COVERAGE_RATIO:
        # as in 20201006_1, 20200125_1, 20200125_2
        return True
    else:
        # as in 20201006_1
        pass
    
    rx_peak_ratio = (x[2] - x[0]) / (xr_curve.x[-1] - xr_curve.x[0])
    uv_peak_ratio = (y[2] - y[0]) / (uv_curve.x[-1] - uv_curve.x[0])
    peak_ratio = min(rx_peak_ratio, uv_peak_ratio)
    if debug:
        print(f"estimate_slope_reliability: peak_ratio={peak_ratio}")
    return peak_ratio >= ACCEPTABLE_2SIGMA_RATIO

def compute_mapping_by_full_coverage(xr_curve, xr_peaks, uv_curve, uv_peaks, debug=False):
    px = xr_curve.x[xr_peaks[0]]
    py = uv_curve.x[uv_peaks[0]]
    """
    py = px * slope + intercept
    Y = X * slope + intercept
        where  (X,Y) == (xr_curve.x[0], uv_curve.x[0])
            or (X,Y) == (xr_curve.x[-1], uv_curve.x[-1])
    """
    X = np.array([xr_curve.x[0], px, xr_curve.x[-1]]).reshape(3, 1)
    y = np.array([uv_curve.x[0], py, uv_curve.x[-1]])

    reg = LinearRegression().fit(X, y,
                                 sample_weight=[0.1, 0.8, 0.1],   # peak top is more important than the edges
                                 )
    slope = reg.coef_[0]
    intercept = reg.intercept_

    if debug:
        print("X=", X.flatten())
        print("y=", y)
        print("compute_mapping_by_full_coverage: slope=", slope, "intercept=", intercept)
    return MappingInfo(slope, intercept, xr_peaks, uv_peaks, None, None, xr_curve, uv_curve)

def estimate_mapping_for_matching_peaks(xr_curve, xr_peaks, uv_curve, uv_peaks, retry=True, debug=False):
    if len(xr_peaks) > 1:
        x = xr_curve.x[xr_peaks]
        y = uv_curve.x[uv_peaks]
        xr_moment = None
        uv_moment = None

    elif len(xr_peaks) == 1:
        from molass.Stats.EghMoment import EghMoment
        xr_moment = EghMoment(xr_curve, num_peaks=1)
        M, std = xr_moment.get_meanstd()
        x = [M - std, M, M + std]
        uv_moment = EghMoment(uv_curve, num_peaks=1)
        M, std = uv_moment.get_meanstd()
        y = [M - std, M, M + std]

    slope, intercept = linregress(x, y)[0:2]
    coverage_ratio = compute_mapping_coverage(xr_curve.x, uv_curve.x, slope, intercept)
    if debug:
        print(f"Mapping coverage: {coverage_ratio}")
    if coverage_ratio >= ACCEPTABLE_COVERAGE_RATIO:
        if xr_moment is not None:
            # that is a case where we have only one peak in xr_curve
            assert len(xr_peaks) == 1, "xr_peaks should have only one peak."
            assert len(x) == 3, "x should have three elements."
            assert len(y) == 3, "y should have three elements."
            reliable = estimate_slope_reliability(xr_curve, x, uv_curve, y, coverage_ratio, debug=debug)
            if not reliable:
                return compute_mapping_by_full_coverage(xr_curve, xr_peaks, uv_curve, uv_peaks, debug=debug)

        return MappingInfo(slope, intercept, xr_peaks, uv_peaks, xr_moment, uv_moment, xr_curve, uv_curve)
    else:
        assert retry, "Mapping coverage is not acceptable after retry."
        xr_curve_ = xr_curve.corrected_copy()
        uv_curve_ = uv_curve.corrected_copy()
        return estimate_mapping_for_matching_peaks(xr_curve_, xr_peaks, uv_curve_, uv_peaks, retry=False, debug=debug)

def estimate_mapping_impl(xr_curve, uv_curve, debug=False):
    from molass.Mapping.Grouping import get_groupable_peaks

    xr_peaks, uv_peaks = get_groupable_peaks(xr_curve, uv_curve, debug=debug)
    if debug:
        print(f"Peaks: xr_peaks={xr_peaks}, uv_peaks={uv_peaks}")

    if len(xr_peaks) == len(uv_peaks):
        """
        note that
            there can be cases where you need to discard minor peaks
            and select matching peaks from the remaining ones.
            e.g.,
            suppose a pair of set of three peaks between which 
            first (_, 1, 2)
               (0, 1, _)
        """
        pass
    else:
        from importlib import reload
        import molass.Mapping.PeakMatcher
        reload(molass.Mapping.PeakMatcher)
        from molass.Mapping.PeakMatcher import select_matching_peaks
        xr_peaks, uv_peaks = select_matching_peaks(xr_curve, xr_peaks, uv_curve, uv_peaks, debug=debug)
        if debug:
            import matplotlib.pyplot as plt
            print("xr_peaks=", xr_peaks)
            print("uv_peaks=", uv_peaks)
            fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10,4))
            fig.suptitle("selected matching peaks")
            for ax, curve, peaks in [(ax1, uv_curve, uv_peaks), (ax2, xr_curve, xr_peaks)]:
                ax.plot(curve.x, curve.y)
                ax.plot(curve.x[peaks], curve.y[peaks], 'o')
            plt.show()

    try:
        return estimate_mapping_for_matching_peaks(xr_curve, xr_peaks, uv_curve, uv_peaks, debug=debug)
    except:
        from molass_legacy.KekLib.ExceptionTracebacker import log_exception
        log_exception(None, "Failed to estimate mapping for matching peaks.", n=5)
        if len(xr_peaks) == 1:
            return compute_mapping_by_full_coverage(xr_curve, xr_peaks, uv_curve, uv_peaks, debug=debug)
        else:
            raise ValueError(
                "Failed to estimate mapping for matching peaks. "
            )