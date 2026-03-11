"""
    Baseline.BufmaskBaseline.py

    Buffer-mask linear polyfit baseline.

    Concept and origin
    ------------------
    This method was proposed by GitHub Copilot (Claude Sonnet 4.5) during an
    interactive session on 2026-03-11, as a direct improvement over the
    Legacy Percentile Method (LPM).

    The key insight (quoted from the session):

        "LPM's core premise is correct: buffer frames have lower intensity
        than protein frames.  But LPM classifies buffer frames implicitly,
        per q-row, under low per-row SNR.  The fix is to lift the
        classification one level up: M.sum(axis=0) collapses all q-rows
        into one curve, gaining √N in SNR.  In that summed elution the
        buffer region is unambiguously flat and low.  Classify buffer frames
        once from this high-SNR oracle, then apply that single mask to
        every q-row for the polyfit."

    In short: the classification question ("is frame j buffer or protein?")
    is a column-level (global) question; LPM answered it row-by-row (local).
    Bufmask answers it once, using the full-matrix aggregate, and reuses
    that answer across all q-rows.

    Performance (SAMPLE1, 2026-03-11)
    ----------------------------------
    Method                          mean positive_ratio
    ----------------------------------
    Old library (p_final fixed 10%) 0.899
    Adaptive p_final / legacy sim   0.716
    Bufmask (threshold = 0.10)      0.578   ← this module
    Ideal (perfect baseline)        ~0.5

    Reference
    ---------
    Implemented in molass-library issue #24.
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
