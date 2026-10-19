"""
    Trimming.AnomalyHandler.py

    Handling of a UV elution curve whose end is irregular (a dip below the baseline in the last frames),
    kept out of the default course of the mapping and the trimming:

    * the XR/UV mapping (``SecSaxsData.estimate_mapping``) calls :func:`estimate_mapping_handling_anomaly`,
      which estimates the mapping on the UV curve *without* the anomalous frames -- i.e. the moments are
      computed after the baseline correction of the cropped curve -- and otherwise is the plain estimation;
    * the trimming (``make_trimming_impl``) calls :func:`cut_uv_end_anomaly`, which only cuts the UV end
      slice and returns it unchanged unless an anomaly is found.

    Why this matters: the dip tilts the baseline estimate, the baseline-corrected UV curve then gets an
    artifact at its end, and the EGH fit of that curve -- the basis of the XR/UV mapping for a single peak per
    channel -- becomes unstable (20200123_3: slope 1.05 or 1.71 depending on an unrelated default).
    Correcting the baseline after excluding the anomalous frames gives a stable result (slope 1.050).

    Detection is two-staged to avoid false positives on ordinary baseline drift:

    1. the baseline of the UV curve *falls* across the curve by at least ``TILT_GATE`` of the peak height;
    2. a dip below the noise band (``DIP_SIGMAS`` robust sigmas) reaches the end of the curve and starts within
       its last ``MAX_DIP_FRACTION``.

    Thresholds were calibrated on 70 local datasets, of which exactly two (20200123_3 and 20190529_2) are
    detected. Only a trailing UV dip is handled so far.
"""
import warnings

import numpy as np
from scipy.signal import savgol_filter

TILT_GATE = 0.2
DIP_SIGMAS = 3.0
MIN_DIP_FRAMES = 5
MAX_DIP_FRACTION = 0.1
MIN_FRAMES = 30
SMOOTHING_WINDOW = 15


def baseline_tilt(curve):
    """Fall of the curve's baseline from the first to the last frame, relative to the peak height.

    The baseline is what the curve correction removes (``y - corrected``). Positive means the
    baseline falls towards the end. Returns 0.0 for a flat curve.
    """
    y = np.asarray(curve.y, dtype=float)
    scale = float(np.max(y) - np.median(y))
    if not scale > 0:
        return 0.0
    baseline = y - np.asarray(curve.corrected_copy().y, dtype=float)
    return float((baseline[0] - baseline[-1]) / scale)


def locate_trailing_dip(y):
    """Index where a dip below the noise band at the end of *y* starts, or ``None``.

    The dip must exceed ``DIP_SIGMAS`` robust sigmas below the median for at least ``MIN_DIP_FRAMES``
    frames, reach the last ``MAX_DIP_FRACTION`` of the curve, and start no earlier than that fraction
    from the end. Its start is where the smoothed curve returns to within one sigma of the median.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    if n < MIN_FRAMES:
        return None
    smooth = savgol_filter(y, SMOOTHING_WINDOW, 3)
    median = np.median(y)
    sigma = 1.4826 * np.median(np.abs(y - median))
    if not sigma > 0:
        return None
    low = np.where(smooth < median - DIP_SIGMAS * sigma)[0]
    if len(low) < MIN_DIP_FRAMES or low.max() < (1 - MAX_DIP_FRACTION) * n:
        return None
    start = int(low.max())
    while start > 0 and smooth[start - 1] < median - sigma:
        start -= 1
    if start < (1 - MAX_DIP_FRACTION) * n:
        return None
    return start


def find_uv_end_anomaly(uv_curve):
    """Start index of an anomalous trailing dip of the UV i-curve, or ``None`` if there is none."""
    if baseline_tilt(uv_curve) < TILT_GATE:
        return None
    return locate_trailing_dip(uv_curve.y)


def estimate_mapping_handling_anomaly(xr_curve, uv_curve, debug=False):
    """Estimate the XR/UV mapping, excluding an anomalous UV end from the estimation.

    Without an anomaly this is :func:`molass.Mapping.SimpleMapper.estimate_mapping_impl`. With one, the
    mapping is estimated on the UV curve cropped at the start of the anomaly (so that the baseline
    correction behind the moments of the retry is not distorted by it) and the result still refers to the
    full UV curve.

    Parameters
    ----------
    xr_curve, uv_curve : Curve
        The XR and UV i-curves.
    debug : bool, optional
        If True, print diagnostic information.

    Returns
    -------
    mapping : MappingInfo
    """
    from molass.Mapping.SimpleMapper import estimate_mapping_impl

    start = find_uv_end_anomaly(uv_curve)
    if start is None:
        return estimate_mapping_impl(xr_curve, uv_curve, debug=debug)

    from molass.DataObjects.Curve import Curve
    from molass.Mapping.MappingInfo import MappingInfo

    n = len(uv_curve.x)
    warnings.warn(
        f"UV elution curve has an irregular end (dip below the baseline from frame {int(uv_curve.x[start])} "
        f"on, {n - start} of {n} frames): excluding it from the XR/UV mapping (and, in trimmed_copy(), "
        f"from the trimming). "
        f"Switch off with molass.Global.Options.set_molass_options(anomaly_handling=False).",
        UserWarning, stacklevel=3,
    )
    cropped = Curve(uv_curve.x[:start], np.asarray(uv_curve.y)[:start], type=uv_curve.type)
    m = estimate_mapping_impl(xr_curve, cropped, debug=debug)
    return MappingInfo(m.slope, m.intercept, m.xr_peaks, m.uv_peaks, m.xr_moment, m.uv_moment, xr_curve, uv_curve)


def cut_uv_end_anomaly(ssd, uv_jslice):
    """Cut an anomalous UV end from the UV frame slice of the trimming.

    Parameters
    ----------
    ssd : SecSaxsData
        The (untrimmed) data being trimmed.
    uv_jslice : slice
        The UV frame slice computed by the default course.

    Returns
    -------
    uv_jslice : slice
        ``uv_jslice`` unchanged when there is no anomaly; otherwise its stop is cut to the start of the
        anomaly. (The mapping is not touched here: ``SecSaxsData.estimate_mapping`` handles the anomaly
        itself and warns.)
    """
    if ssd.uv is None or ssd.xr is None:
        return uv_jslice
    start = find_uv_end_anomaly(ssd.uv.get_icurve())
    if start is None:
        return uv_jslice
    stop = start if uv_jslice.stop is None else min(uv_jslice.stop, start)
    return slice(uv_jslice.start, stop)
