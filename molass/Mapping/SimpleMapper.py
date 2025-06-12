"""
    Mapping.SimpleMapperpy

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
from scipy.stats import linregress
from molass.Mapping.MappingInfo import MappingInfo

ACCEPTABLE_COVERAGE_RATIO = 0.6

def check_mapping_coverage(x, y, slope, intercept, debug=False):
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

    if debug:
        print(f"Mapping coverage: {coverage_ratio}")
    return coverage_ratio >= ACCEPTABLE_COVERAGE_RATIO

def estimate_mapping_for_matching_peaks(xr_curve, xr_peaks, uv_curve, uv_peaks, retry=True):
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
    if check_mapping_coverage(xr_curve.x, uv_curve.x, slope, intercept):
        return MappingInfo(slope, intercept, xr_peaks, uv_peaks, xr_moment, uv_moment, xr_curve, uv_curve)
    else:
        assert retry, "Mapping coverage is not acceptable."
        xr_curve_ = xr_curve.corrected_copy()
        uv_curve_ = uv_curve.corrected_copy()
        return estimate_mapping_for_matching_peaks(xr_curve_, xr_peaks, uv_curve_, uv_peaks, retry=False)

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

    return estimate_mapping_for_matching_peaks(xr_curve, xr_peaks, uv_curve, uv_peaks)
