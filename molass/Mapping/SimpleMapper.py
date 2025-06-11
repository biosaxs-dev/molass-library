"""
    Mapping.SimpleMapperpy

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
from scipy.stats import linregress
from molass.Mapping.MappingInfo import MappingInfo

def estimate_mapping_for_matching_peaks(xr_curve, xr_peaks, uv_curve, uv_peaks):
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
    return MappingInfo(slope, intercept, xr_peaks, uv_peaks, xr_moment, uv_moment, xr_curve, uv_curve)

def estimate_mapping_impl(xr_curve, uv_curve, debug=False):
    xr_peaks = xr_curve.get_peaks(debug=debug)
    uv_peaks = uv_curve.get_peaks(debug=debug)
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
