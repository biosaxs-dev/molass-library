"""
Bridge.LegacyRgCurve.py
"""
import numpy as np
from molass_legacy.RgProcess.RgCurve import RgCurve, make_availability_slices
from molass_legacy._MOLASS.SerialSettings import get_setting

class LegacyRgCurve(RgCurve):
    """A class representing a legacy Rg curve.

    Inherits from the legacy ``molass_legacy.RgProcess.RgCurve.RgCurve`` but
    bypasses ``super().__init__()``.  The following parent attributes that would
    normally be set by the parent ``__init__`` must therefore be initialized
    manually here — any future extension of this class or new subclass of
    ``RgCurve`` must do the same:

    - ``self.ecurve``        — required by ``add_exclspline()``
    - ``self.excl_spline``   — checked by ``get_rgs_from_trs()`` (lazy build)
    - ``self.excl_info``     — set by ``add_exclspline()``
    - ``self.X``             — used by ``get_probabilistic_data()``
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
        rg_qualities = np.ones(len(x)) * np.nan
        # Convert absolute frame indices to 0-based relative indices
        frame_offset = int(x[0])
        rel_indices = rgcurve.indeces - frame_offset
        mask = (rel_indices >= 0) & (rel_indices < len(x))
        rg_values[rel_indices[mask]] = rgcurve.rgvalues[mask]
        rg_qualities[rel_indices[mask]] = rgcurve.scores[mask]
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
        # Required by RgCurve.add_exclspline() (called lazily by get_rgs_from_trs).
        self.ecurve = ecurve
        self.excl_spline = None   # built on first call to get_rgs_from_trs()
        self.excl_info = None
        self.X = None             # used by get_probabilistic_data()