"""
    LowRank.Component.py

    This module contains the class Component, which is used to store information
    about each component of a LowRankInfo.
"""
import numpy as np
from scipy.interpolate import UnivariateSpline
from scipy.optimize import minimize
import scipy.integrate as integrate

SAFE_AVOID_WIDTH = 5
LOW_VALUE_RATIO = 0.01

class Component:
    """
    A class to represent a component.
    """
    def __init__(self, icurve_array, jcurve_array):
        """
        """
        self.icurve_array = icurve_array
        self.jcurve_array = jcurve_array
        x, y = self.icurve_array
        self.peak_index = np.argmax(y)
        self.spline = None
        self.area = None

    def get_icurve(self):
        """
        Returns the i-curve object.
        """
        from molass.DataObjects.Curve import Curve
        return Curve(*self.icurve_array[0:2], type='i')

    def get_jcurve(self):
        """
        Returns the j-curve object.
        """
        from molass.DataObjects.Curve import Curve
        return Curve(*self.jcurve_array[:,0:2], type='j')

    def get_jcurve_array(self):
        """
        Returns the j-curve array which contains qv, I and error in case of XR.

        Currently, error is zeros in case of UV.
        """
        return self.jcurve_array

    def compute_area(self):
        if self.area is None:
            x, y = self.icurve_array[:,0:2]
            self.spline = UnivariateSpline(x, y, s=0)
            self.area = integrate.quad(self.spline, x[0], x[-1])[0]            
        return self.area

    def compute_range(self, area_ratio, debug=False, return_also_fig=False):
        x, y = self.icurve_array[:,0:2]
        entire_area = self.compute_area()
        entire_spline = self.spline
        target_area = entire_area*area_ratio
        m = self.peak_index
        if debug:
            print("m=", m, "area_ratio=", area_ratio, "target_area=", target_area)

        # search for the suffciently large ends to avoid the strictly increasing issue
        # of UnivariateSpline when s=0
        low_y = y[m]*LOW_VALUE_RATIO
        where_low = np.where(y > low_y)[0]

        asc_start = where_low[0]
        asc_stop = m - SAFE_AVOID_WIDTH + 1
        asc_spline = UnivariateSpline(y[asc_start:asc_stop], x[asc_start:asc_stop], s=0)
        dsc_start = m + SAFE_AVOID_WIDTH
        dsc_stop = where_low[-1]
        y_ = np.flip(y[dsc_start:dsc_stop])
        x_ = np.flip(x[dsc_start:dsc_stop])
        dsc_spline = UnivariateSpline(y_, x_, s=0)
        x0 = int(x[0])

        def ratio_fit_func(p, return_range=False, debug=False):
            height = p[0]
            asc_x = asc_spline(height)
            dsc_x = dsc_spline(height)

            if return_range:
                start = int(asc_x+0.5) - x0
                stop = int(dsc_x+0.5) - x0 + 1
                return start, stop, asc_x, dsc_x
            
            range_area = integrate.quad(entire_spline, asc_x, dsc_x)[0]     # using integrate not np.sum(...) to avoid the smoothness issue
            ret_val = (range_area - target_area)**2
            if debug:
                print("height=", height, "range_area=", range_area, "ret_val=", ret_val)
            return ret_val

        init_height = y[m]/2
        res = minimize(ratio_fit_func, (init_height, ), method='Nelder-Mead')
        start, stop, asc_x, dsc_x = ratio_fit_func(res.x, return_range=True, debug=debug)

        if debug:
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(ncols=2, figsize=(10,4))
            fig.suptitle("%g-area ratio Range of the Component with Peak at %g" % (area_ratio, x[m]))
            for ax in axes:
                ax.plot(x, y, color='gray', alpha=0.5)
                ax.plot(asc_spline(y[:m]), y[:m])
                ax.plot(dsc_spline(y[m:]), y[m:])
                ax.axhline(res.x[0])
                if False:
                    for i in start, stop-1:
                        ax.axvline(x[i], color="yellow", alpha=0.5)
            
                ax.fill_between(x, y, color='gray', alpha=0.3, label='entire peak area')
                ax.fill_between(x, y, where=(x > asc_x) & (x < dsc_x), color='cyan', alpha=0.3, label='selected area')

                for px in asc_x, dsc_x:
                    ax.axvline(px, color="green", alpha=0.5)
                
                ax.legend()
            axes[1].set_xlim(asc_x - 5, dsc_x + 5)
            if return_also_fig:
                return start, stop, fig

        return start, stop
    
    def make_paired_range(self, range_, minor=False):
        from molass.LowRank.PairedRange import PairedRange
        return PairedRange(range_, minor=minor, peak_index=self.xr_peak_index)

class XrComponent(Component):
    """
    A class to represent an XR component.
    """
    def __init__(self, *args):
        super().__init__(*args)

    def compute_rg(self, return_object=False):
        """
        """
        from molass_legacy.GuinierAnalyzer.SimpleGuinier import SimpleGuinier
        sg = SimpleGuinier(self.jcurve_array)
        if return_object:
            return sg
        else:
            return sg.Rg
class UvComponent(Component):
    """
    A class to represent a UV component.
    """
    def __init__(self, *args):
        super().__init__(*args)