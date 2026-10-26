"""
    Homogeneity.Proxies.py

    Concentration proxies: 1-D curves on the XR frames that are (to first order)
    proportional to the concentration of the eluting material. Ratios of two
    proxies (see :mod:`molass.Homogeneity.Ratios`) are flat across a peak of a
    single species.
"""
import numpy as np


class ConcentrationProxy:
    """A curve on the XR frames used as a concentration proxy.

    Attributes
    ----------
    name : str
        Display name, e.g. ``"I(0)"``, ``"I(0.02)"``, ``"A280"``.
    frames : np.ndarray
        XR frame numbers.
    values : np.ndarray
        Proxy values at ``frames``; NaN where not available.
    source : str
        ``"xr"`` or ``"uv"``.
    uses_mapping : bool
        True if the values depend on the UV->XR mapping (UV proxies).
    params : dict
        How the proxy was made (q, wavelength, half width, mapping shift ...).
    """

    def __init__(self, name, frames, values, source, uses_mapping=False, params=None):
        frames = np.asarray(frames)
        values = np.asarray(values, dtype=float)
        if len(frames) != len(values):
            raise ValueError("frames and values must have the same length")
        if source not in ("xr", "uv"):
            raise ValueError("source must be 'xr' or 'uv'")
        self.name = name
        self.frames = frames
        self.values = values
        self.source = source
        self.uses_mapping = bool(uses_mapping)
        self.params = dict(params or {})

    def __repr__(self):
        return f"ConcentrationProxy({self.name!r}, source={self.source!r}, uses_mapping={self.uses_mapping})"


def band_average(M, axis_values, center, half_width):
    """Mean of the rows of ``M`` whose ``axis_values`` lie within ``center +- half_width``."""
    axis_values = np.asarray(axis_values)
    rows = np.abs(axis_values - center) <= half_width
    if not rows.any():
        raise ValueError(f"no data within {center} +- {half_width}"
                         f" (range {axis_values.min():.4g} to {axis_values.max():.4g})")
    return np.asarray(M)[rows].mean(axis=0)


def xr_i0_proxy(rgcurve, min_score=None):
    """I(0) of the per-frame Guinier fits (see ``RgCurve.i0s``) as a proxy named ``"I(0)"``.

    Concentration times molar mass of the species in the frame, with the usual
    caveats of a Guinier extrapolation (NaN where a fit failed).

    Parameters
    ----------
    rgcurve : RgCurve
    min_score : float or None
        If given, frames whose Guinier fit score is below it are set to NaN.
    """
    values = np.array(rgcurve.i0s, dtype=float)
    if min_score is not None:
        values[np.asarray(rgcurve.scores, dtype=float) < min_score] = np.nan
    return ConcentrationProxy("I(0)", rgcurve.frames, values, "xr")


def xr_q_proxy(xr, q, half_width=None):
    """Intensity at scattering angle ``q`` (1/A), averaged over ``q +- half_width``, as ``"I(q)"``.

    Parameters
    ----------
    xr : XrData
        Corrected XR data (``ssd.xr``).
    q : float
        Centre of the band in 1/A.
    half_width : float or None
        Half width of the band in 1/A; None means three q steps.
    """
    qv = np.asarray(xr.qv)
    if half_width is None:
        half_width = 3 * np.median(np.diff(qv))
    values = band_average(xr.M, qv, q, half_width)
    return ConcentrationProxy(f"I({q:g})", xr.jv, values, "xr",
                              params=dict(q=q, half_width=half_width))


def uv_proxy(uv, wavelength, mapping, frames, delta=0.0, half_width=2.5):
    """Absorbance at ``wavelength`` (nm) mapped onto the XR ``frames``, as ``"A<wavelength>"``.

    Parameters
    ----------
    uv : UvData
        Corrected UV data (``ssd.uv``).
    wavelength : float
        Centre of the band in nm.
    mapping : MappingInfo
        The UV->XR mapping (``ssd.get_mapping()``); XR frame f corresponds to UV frame
        ``slope * (f - delta) + intercept``.
    frames : array-like
        XR frame numbers to evaluate at (e.g. ``xr.jv``).
    delta : float
        Shift of the mapping in XR frames (+ = later); 0 is the estimated mapping.
    half_width : float
        Half width of the band in nm.

    Notes
    -----
    Values are NaN where the mapped UV frame lies outside the UV frame range.
    """
    frames = np.asarray(frames)
    band = band_average(uv.M, uv.wv, wavelength, half_width)
    uv_frames = mapping.xr_to_uv(frames - delta)
    values = np.interp(uv_frames, uv.jv, band, left=np.nan, right=np.nan)
    return ConcentrationProxy(f"A{wavelength:g}", frames, values, "uv", uses_mapping=True,
                              params=dict(wavelength=wavelength, half_width=half_width, delta=delta))
