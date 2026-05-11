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

    Handles both concrete boolean arrays (from ``corrected_copy()``) and
    ``slice`` objects (stored by ``set_anomaly_mask()`` on trimmed data),
    converting the latter to a boolean array over ``jv``.
    """
    xr = ssd.xr
    xr_mask = getattr(xr, 'anomaly_mask', None)

    if xr_mask is None:
        return None, None

    jv = xr.jv

    # Slice stored by set_anomaly_mask() — convert to boolean array over jv
    if isinstance(xr_mask, slice):
        bool_mask = np.zeros(len(jv), dtype=bool)
        i0 = np.searchsorted(jv, xr_mask.start)
        i1 = np.searchsorted(jv, xr_mask.stop, side='right')
        bool_mask[i0:i1] = True
        if bool_mask.any():
            return jv, bool_mask
        return None, None

    # Concrete boolean array (from corrected_copy())
    if hasattr(xr_mask, 'any') and xr_mask.any():
        return jv, xr_mask

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
