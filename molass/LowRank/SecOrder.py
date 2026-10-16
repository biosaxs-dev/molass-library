"""
LowRank.SecOrder.py

SEC-conformance check of a decomposition (molass-library#296).

In size-exclusion chromatography larger particles elute first, so the component Rgs
(obtained by the LRF) should decrease with elution order, and each component's Rg
should resemble the Rg curve at its peak position.
"""
import numpy as np

# same soft tolerance (Angstrom) as the rigorous objective's Rg order penalty
DEFAULT_TOLERANCE = 2.0
# half-width (frames) of the window over which the Rg curve is averaged at a peak position
RG_CURVE_HALF_WINDOW = 5


class SecOrderReport:
    """Result of :meth:`molass.LowRank.Decomposition.Decomposition.check_sec_order`.

    Attributes
    ----------
    rgs : ndarray
        Component Rgs (Angstrom) in component order (NaN where the Guinier fit failed).
    positions : ndarray
        Component peak positions (frames).
    rg_curve_values : ndarray or None
        Median of the Rg curve within +-5 frames of each peak position; None if no Rg curve was available.
    relative_deviations : ndarray or None
        ``(rgs - rg_curve_values) / rg_curve_values``; None if no Rg curve was available.
    violations : list of tuple
        ``(i, j, reversal)`` for each adjacent pair (i, j=i+1) whose Rg *increases* by more than
        ``tolerance`` (``reversal = rgs[j] - rgs[i]`` in Angstrom, component indices are 0-based).
    tolerance : float
        Allowed reversal in Angstrom.
    ordered : bool
        True if there is no violation (NaN Rgs make it False).
    """

    def __init__(self, rgs, positions, rg_curve_values, tolerance):
        self.rgs = np.asarray(rgs, dtype=float)
        self.positions = np.asarray(positions, dtype=float)
        self.rg_curve_values = None if rg_curve_values is None else np.asarray(rg_curve_values, dtype=float)
        self.tolerance = tolerance
        if self.rg_curve_values is None:
            self.relative_deviations = None
        else:
            self.relative_deviations = (self.rgs - self.rg_curve_values) / self.rg_curve_values
        self.violations = []
        for i in range(len(self.rgs) - 1):
            reversal = self.rgs[i + 1] - self.rgs[i]
            if reversal > tolerance:
                self.violations.append((i, i + 1, float(reversal)))
        self.ordered = not self.violations and not np.any(np.isnan(self.rgs))

    def __bool__(self):
        return self.ordered

    def __repr__(self):
        lines = [f"SecOrderReport(ordered={self.ordered}, tolerance={self.tolerance:g} A)"]
        header = "  comp  position      Rg"
        if self.rg_curve_values is not None:
            header += "   RgCurve   deviation"
        lines.append(header)
        for k, (pos, rg) in enumerate(zip(self.positions, self.rgs)):
            row = f"  {k + 1:>4}  {pos:8.1f}  {rg:7.2f}"
            if self.rg_curve_values is not None:
                row += f"  {self.rg_curve_values[k]:8.2f}  {self.relative_deviations[k] * 100:+8.1f}%"
            lines.append(row)
        for i, j, reversal in self.violations:
            lines.append(f"  violation: Rg increases from component {i + 1} to {j + 1} by {reversal:.2f} A")
        return "\n".join(lines)


def rg_curve_at(rgcurve, position, half_window=RG_CURVE_HALF_WINDOW):
    """Median Rg-curve value within +-half_window frames of *position* (NaN if none)."""
    frames = np.asarray(rgcurve.indeces)
    values = np.asarray(rgcurve.rgvalues, dtype=float)
    sel = (np.abs(frames - position) <= half_window) & np.isfinite(values) & (values > 0)
    return float(np.median(values[sel])) if sel.any() else float('nan')


def check_sec_order_impl(decomposition, rgcurve=None, tolerance=DEFAULT_TOLERANCE, compute_rg_curve=False):
    if rgcurve is None and (compute_rg_curve or decomposition.has_rg_curve):
        rgcurve = decomposition.get_rg_curve()
    rgs = decomposition.get_rgs()
    positions = [float(c.get_peak_position()) for c in decomposition.xr_ccurves]
    rg_curve_values = None
    if rgcurve is not None:
        rg_curve_values = [rg_curve_at(rgcurve, p) for p in positions]
    return SecOrderReport(rgs, positions, rg_curve_values, tolerance)
