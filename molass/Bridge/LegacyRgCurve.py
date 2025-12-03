"""
Bridge.LegacyRgCurve.py
"""
import numpy as np
from molass_legacy.RgProcess.RgCurve import RgCurve, make_availability_slices
from molass_legacy._MOLASS.SerialSettings import get_setting

class LegacyRgCurve(RgCurve):
    """
    A class representing a legacy Rg curve.
    """

    def __init__(self, ecurve, rgcurve):
        """
        Initializes the LegacyRgCurve with the given Rg values.

        Parameters
        ----------
        rg_values : list of float
            The Rg values for each component.
        """
        self.x = x = ecurve.x
        self.y = y = ecurve.y
        rg_values = np.ones(len(x)) * np.nan
        rg_values[rgcurve.indeces] = rgcurve.rgvalues
        rg_qualities = np.ones(len(x)) * np.nan
        rg_qualities[rgcurve.indeces] = rgcurve.scores
        slices, states = make_availability_slices(y, ecurve.max_y)
        self.slices = slices
        self.states = states
        segments = []
        qualities = []
        for slice_, state in zip(slices, states):
            if state == 0:
                continue
            segments.append((x[slice_], y[slice_], rg_values[slice_]))
            qualities.append(rg_qualities[slice_])
        self.segments = segments
        self.qualities = qualities
        xr_restrict_list = get_setting("xr_restrict_list")
        self.rg_trimming = None if xr_restrict_list is None else xr_restrict_list[0]
        self.baseline_type = get_setting("unified_baseline_type")