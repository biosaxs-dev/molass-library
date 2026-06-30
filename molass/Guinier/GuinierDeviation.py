"""
Guinier.GuinierDeviation.py

Computes the Guinier deviation score used in rigorous optimization.
Canonical location: molass-library.  molass_legacy.GuinierTools.GuinierDeviation
re-exports from here.

Copyright (c) 2023-2025, SAXS Team, KEK-PF
"""
import logging
from bisect import bisect_right
import numpy as np
from scipy.stats import linregress
from molass.Guinier.RgEstimator import RgEstimator as SimpleGuinier
from molass.Guinier.RgCurveUtils import (
    get_connected_curve_info, convert_to_milder_qualities, VALID_BASE_QUALITY,
)

USE_NORMALIZED_RMSD_FOR_RGCURVES = True

VERY_SMALL_VALUE = 1e-10
GN_DEV_LOWER_LIMIT = -2     # exceeding this to lower values may result in abnormal states
RG_DEV_LOWER_LIMIT = -2     # same as above
MAXIMIZE_ADJUST = -1.5      # this value balances the optimization among [Guinier_deviation, SEC_conformance, FIT_max]
                            # i.e., the greater this value, the more weight for Guinier_deviation
NEGATIVE_SLOPE_SCALE = 1e3
QRG_UPPER_BOUND = 1.3
USE_GUINIER_RGS = True
BAD_RG_VALUE = -1
MIN_RG = 5                  # to avoid abnormal situations as in 20191118_4 with 4 components by STC_MP where Rg < 5Å


class GuinierDeviation:
    def __init__(self, qv, rg_curve, rg_params, region_limit=0, composite=None):
        self.logger = logging.getLogger(__name__)
        self.qv = qv
        self.rg_curve = rg_curve
        x_, y_, rgv, qualities, valid_bools = get_connected_curve_info(rg_curve)
        self.x_ = x_
        self.y_ = y_
        self.rgv = rgv[valid_bools.segment]
        self.mqualities = convert_to_milder_qualities(qualities)
        self.max_mask = self.mqualities > VALID_BASE_QUALITY
        self.raw_qualities = qualities[valid_bools.segment]  # raw qualities: tail frames get ~0 weight
        # Apply combined weight w(j) = q(j) * Ĩ(j) where Ĩ(j) = I(j)/I_peak.
        # This suppresses buffer frames that have low intensity (and thus uninformative Rg)
        # even if their Guinier quality score is not zero.
        # Both factors are ∈ [0,1] so w ∈ [0,1] — no scale change needed.
        y_seg = y_[valid_bools.segment]
        I_peak = np.max(y_seg) if len(y_seg) > 0 else 1.0
        I_norm_seg = y_seg / I_peak if I_peak > 0 else np.ones(len(y_seg))
        self.weights = self.raw_qualities * I_norm_seg  # w(j) = q(j) * Ĩ(j)
        self.valid_bools = valid_bools
        self.valid_size = len(np.where(valid_bools.segment)[0])

        assert composite is not None
        self.composite = composite
        self.update_region(rg_params, region_limit)  # this only roughly determines the region,
                                                     # which is to be refined later by update_region with P assigned
                                                     # in BasicOptimizer.update_guinier_region

    def update_region(self, rg_params, region_limit, P=None, M=None, E=None, debug=False):
        i0 = bisect_right(self.qv, region_limit)
        i1_rough_limit = len(self.qv) // 2    # to avoid abnormal situations as in 20191118_4 with 4 components by STC_MP where Rg < 5Å
        self.gslices = []
        self.qv2s = []
        self.low_vecs = []
        self.rgs = np.ones(len(rg_params)) * np.nan
        self.izs = np.ones(len(rg_params)) * np.nan
        if P is None:
            pass
        else:
            # see also Optimizer.LrfExporter.XrLrfResult
            X = np.linalg.pinv(M) @ P       # M or M_
            Ep = np.sqrt((E**2) @ (X**2))
        valid_rgs = self.composite.get_valid_rgs(rg_params)
        if debug:
            data_list = []
            qualities = []
        for k, rg in enumerate(valid_rgs):
            if P is None:
                q = QRG_UPPER_BOUND / max(MIN_RG, rg)
                i1 = min(i1_rough_limit, max(i0 + 2, bisect_right(self.qv, q)))
                gslice = slice(i0, i1)
                iz = 1  # dummy, immediately replaced by the following values
            else:
                y = P[:, k]
                e = Ep[:, k]
                data = np.array([self.qv, y, e]).T
                sg = SimpleGuinier(data)
                if sg.Rg is None:
                    q = QRG_UPPER_BOUND / max(MIN_RG, rg)
                    i1 = min(i1_rough_limit, max(i0 + 2, bisect_right(self.qv, q)))
                    gslice = slice(i0, i1)
                    iz = y[i0]
                else:
                    self.rgs[k] = sg.Rg
                    i0_ = bisect_right(self.qv, sg.min_q)
                    i1 = bisect_right(self.qv, sg.max_q)
                    gslice = slice(i0_, i1)
                    iz = sg.Iz
                if debug:
                    data_list.append(data)
                    qualities.append(sg.basic_quality)
            self.gslices.append(gslice)
            self.qv2s.append(self.qv[gslice]**2)
            self.izs[k] = iz
            self.low_vecs.append(np.ones(gslice.stop - gslice.start) * VERY_SMALL_VALUE)

        if debug:
            import molass_legacy.KekLib.DebugPlot as plt
            print("rg_params=", rg_params)
            print("self.gslices=", self.gslices)
            qv2w = self.qv**2

            max_stop = np.max([slice_.stop for slice_ in self.gslices])
            min_rg = np.min(valid_rgs)
            lim_q = 1.8 / min_rg
            max_stop = max(max_stop, bisect_right(self.qv, lim_q))

            indeces = [str(i) for i in range(len(qualities))]
            with plt.Dp():
                fig, (ax0, ax1, ax2) = plt.subplots(ncols=3, figsize=(18, 5))
                fig.suptitle("Debug Plot for update_region", fontsize=20)
                ax0.set_title("Linear Plot", fontsize=16)
                ax1.set_title("Guinier Plot", fontsize=16)
                ax2.set_title("Rg Basic Qualities", fontsize=16)
                k = 0
                for gslice, qv2, data in zip(self.gslices, self.qv2s, data_list):
                    lin_y = data[:, 1]
                    ax0.plot(self.qv, lin_y, label="$R_g$=%.3g" % self.rgs[k])
                    log_y = np.log(lin_y)
                    ax1.plot(qv2w[0:max_stop], log_y[0:max_stop], label="$R_g$=%.3g" % self.rgs[k])
                    ax1.plot(qv2, log_y[gslice], "o", color="yellow")
                    k += 1
                ax0.legend()
                ax1.legend()
                ax2.bar(indeces, qualities)
                fig.tight_layout()
                ret = plt.show()
                if not ret:
                    return

        regions = [self.qv[[gslice.start, min(gslice.stop, len(self.qv) - 1)]] for gslice in self.gslices]
        self.logger.info("updated regions=%s", str(regions))
        if P is not None:
            self.logger.info("updated rgs=%s", str(self.rgs))

        return True

    def compute_deviation(self, P, Cxr, rg_params, valid_components=None, return_details=False, debug=False):
        if valid_components is None:
            valid_components = np.ones(len(rg_params), dtype=bool)
        dev1 = 0
        dev2 = 0
        nc = self.composite.get_num_substantial_components()    # excluding the baseline
        valid_rgs = self.composite.get_valid_rgs(rg_params)
        n = 0
        lrf_rgs = []
        for k, p in enumerate(P.T[0:nc]):
            if not valid_components[k]:
                # continue
                pass

            x = self.qv2s[k]
            y = np.log(np.max([self.low_vecs[k], p[self.gslices[k]]], axis=0))
            slope, intercept, r_value, p_value, std_err = linregress(x, y)

            if slope < 0:
                rg = np.sqrt(-3 * slope)
            else:
                rg = BAD_RG_VALUE                   # to avoid nan values
                std_err *= NEGATIVE_SLOPE_SCALE     # indicating it is undesirable

            lrf_rgs.append(rg)

            dev1 += std_err**2
            if USE_GUINIER_RGS:
                if not np.isnan(self.rgs[k]):
                    dev2 += (self.rgs[k] - valid_rgs[k])**2
            else:
                dev2 += (rg - valid_rgs[k])**2
            n += 1

        gdev = max(GN_DEV_LOWER_LIMIT, np.log10(dev1)) + MAXIMIZE_ADJUST
        if n == 0:
            # to avoid division by zero in dev2/n
            n = 1
        rdev = max(RG_DEV_LOWER_LIMIT, np.log10(dev2 / n)) + MAXIMIZE_ADJUST
        ret_val = ((gdev + rdev) / 2 + max(gdev, rdev)) / 2
        if debug:
            from importlib import reload
            import molass_legacy.KekLib.DebugPlot as plt

            def rg_deviation_inspect():
                import molass_legacy.GuinierTools.RgCurveUtils
                reload(molass_legacy.GuinierTools.RgCurveUtils)
                from molass_legacy.GuinierTools.RgCurveUtils import rg_deviation_inspect_impl
                rg_deviation_inspect_impl(self, valid_components, rg_params, lrf_rgs)

            def compare_dist_measures():
                import molass_legacy.GuinierTools.CompareGdevMeasures
                reload(molass_legacy.GuinierTools.CompareGdevMeasures)
                from molass_legacy.GuinierTools.CompareGdevMeasures import compare_gdev_measures_impl
                print("ret_val=", ret_val)
                compare_gdev_measures_impl(self, Cxr, rg_params, valid_components)

            extra_button_specs = [
                ("inspect", rg_deviation_inspect),
                ("compare", compare_dist_measures),
            ]

            with plt.Dp(button_spec=["OK", "Cancel"], extra_button_specs=extra_button_specs):
                fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(12, 5))
                fig.suptitle("compute_deviation")
                ax1.bar(["dev1", "dev2"], [dev1, dev2])
                ax2.bar(["adjust", "glimit", "gdev", "rlimit", "rdev", "ret_val"],
                        [MAXIMIZE_ADJUST, GN_DEV_LOWER_LIMIT, gdev, RG_DEV_LOWER_LIMIT, rdev, ret_val])
                fig.tight_layout()
                ret = plt.show()
            if not ret:
                return

        if return_details:
            return gdev, rdev
        else:
            return ret_val

    def compute_rgcurve_deviation(self, Cxr, rg_params, adjust=0, debug=False):
        from molass.Guinier.RgCurveUtils import get_reconstructed_curve

        rrgv = get_reconstructed_curve(self.valid_size, self.valid_bools, Cxr, rg_params)
        if debug:
            import molass_legacy.KekLib.DebugPlot as plt
            with plt.Dp():
                fig, ax = plt.subplots()
                ax.set_title("get_reconstructed_curve: debug")
                ax.plot(self.rgv, label='guinier measured')
                ax.plot(rrgv, label='reconstructed')
                ax.legend()
                fig.tight_layout()
                plt.show()

        if USE_NORMALIZED_RMSD_FOR_RGCURVES:
            from molass_legacy.Distance.NormalizedRmsd import normalized_rmsd
            return normalized_rmsd(self.rgv, rrgv, weights=self.weights, adjust=adjust)
        else:
            from molass_legacy.Distance.FrobeniusXdiffmax import frobenius_xdiffmax
            return frobenius_xdiffmax(self.rgv, rrgv, adjust=adjust, max_mask=self.max_mask)
