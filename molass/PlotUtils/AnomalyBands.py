"""
    PlotUtils.AnomalyBands.py

    Shared utility for drawing anomaly exclusion bands across all plot types
    (plot_compact, plot_components, MplMonitor).
"""
import numpy as np

ANOMALY_BAND_COLOR = 'red'
ANOMALY_BAND_ALPHA = 0.08


def get_anomaly_mask_from_ssd(ssd):
    """Extract the XR anomaly mask from an SSD object.

    Returns (jv, mask) where mask is a boolean array, or (None, None)
    if no anomaly information is available.

    Only returns a mask when ``corrected_copy()`` has cached a concrete
    boolean array in ``xr.anomaly_mask``.  The auto-detect mode
    (``has_anomaly_mask=True``, ``anomaly_mask=None``) is NOT resolved
    here because the recognition-curve test only makes sense after
    baseline correction.
    """
    xr = ssd.xr
    xr_mask = getattr(xr, 'anomaly_mask', None)

    if xr_mask is not None and hasattr(xr_mask, 'any') and xr_mask.any():
        return xr.jv, xr_mask

    return None, None


def draw_anomaly_bands(ax, jv, mask, color=None, alpha=None):
    """Draw shaded vertical bands for contiguous runs of True in *mask*.

    Parameters
    ----------
    ax : matplotlib Axes
        The axes to draw on.
    jv : array-like
        Frame indices (x-axis values).
    mask : array-like of bool
        True for anomalous frames.
    color : str, optional
        Band color. Default: 'red'.
    alpha : float, optional
        Band transparency. Default: 0.08.
    """
    if mask is None or not np.any(mask):
        return
    if color is None:
        color = ANOMALY_BAND_COLOR
    if alpha is None:
        alpha = ANOMALY_BAND_ALPHA

    idx = np.where(mask)[0]
    if len(idx) == 0:
        return
    breaks = np.where(np.diff(idx) > 1)[0] + 1
    for group in np.split(idx, breaks):
        lo, hi = jv[group[0]], jv[group[-1]]
        ax.axvspan(lo, hi, color=color, alpha=alpha, zorder=0)


def draw_anomaly_bands_for_ssd(xr_ax, uv_ax, ssd):
    """Draw anomaly bands on XR and UV axes using SSD anomaly info.

    Parameters
    ----------
    xr_ax : matplotlib Axes
        XR elution axis.
    uv_ax : matplotlib Axes or None
        UV elution axis (may be twin axis).
    ssd : SecSaxsData
        The data object carrying anomaly mask information.
    """
    jv, mask = get_anomaly_mask_from_ssd(ssd)
    if jv is None:
        return

    draw_anomaly_bands(xr_ax, jv, mask)

    # Map XR anomaly frames to UV axis via channel mapping
    if uv_ax is not None and ssd.uv is not None:
        mapping = ssd.get_mapping()
        if mapping is not None and not isinstance(mapping, tuple):
            uv_jv = ssd.uv.jv
            xr_frames_excluded = jv[mask]
            uv_frames_mapped = mapping.slope * xr_frames_excluded + mapping.intercept
            uv_lo, uv_hi = uv_frames_mapped.min(), uv_frames_mapped.max()
            uv_mask = (uv_jv >= uv_lo) & (uv_jv <= uv_hi)
            draw_anomaly_bands(uv_ax, uv_jv, uv_mask)
