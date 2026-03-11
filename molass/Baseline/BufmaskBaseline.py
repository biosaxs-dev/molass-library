"""
    Baseline.BufmaskBaseline.py

    Buffer-mask linear polyfit baseline.

    Uses the summed elution curve (high SNR) to classify buffer frames,
    then fits a straight line through those frames only via np.polyfit.
    This is more direct than the iterative LPM percentile descent and
    yields a lower (more correct) positive_ratio in buffer regions.
"""
import numpy as np

BUFMASK_THRESHOLD = 0.10   # fraction of peak below which a frame is buffer


def compute_bufmask_baseline(x, y, return_also_params=False, **kwargs):
    """Compute a linear baseline anchored on buffer frames only.

    Parameters
    ----------
    x : array-like
        Frame indices (jv).
    y : array-like
        Intensity elution profile at one q-value.
    return_also_params : bool, optional
        If True, return ``(baseline, params_dict)``.
    **kwargs : dict
        Must contain ``buffer_mask`` (bool array, shape == y.shape),
        pre-computed once from the summed elution by ``SsMatrixData``.

    Returns
    -------
    baseline : ndarray
    params : dict  (only if return_also_params is True)
        Keys: ``slope``, ``intercept``, ``n_buffer``.
    """
    buffer_mask = kwargs.get('buffer_mask', None)
    if buffer_mask is None or buffer_mask.sum() < 2:
        # Fallback: use all frames
        slope, intercept = np.polyfit(x, y, 1)
    else:
        slope, intercept = np.polyfit(x[buffer_mask], y[buffer_mask], 1)

    baseline = x * slope + intercept
    if return_also_params:
        n_buffer = int(buffer_mask.sum()) if buffer_mask is not None else len(x)
        return baseline, dict(slope=slope, intercept=intercept, n_buffer=n_buffer)
    return baseline
