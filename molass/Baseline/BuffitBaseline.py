"""
    Baseline.BuffitBaseline.py

    Buffer-fit (buffer-frame polyfit) baseline.

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
    Buffit answers it once, using the full-matrix aggregate, and reuses
    that answer across all q-rows.

    Performance (7 SEC-SAXS datasets, 2026-03-11/12)
    --------------------------------------------------
    Method                          mean positive_ratio (range)
    --------------------------------------------------
    Old library (p_final fixed 10%) 0.899
    Adaptive p_final / legacy sim   0.716
    Buffit  (threshold = 0.10)      0.578          (single dataset)
    Buffit  (fixed 10%, all 7)      0.529 – 0.600
    arpls                           0.552 – 0.590
    Buffit  (Otsu, default)         0.496 – 0.522  ← recommended
    Ideal (perfect baseline)        ~0.5

    Otsu wins all 7 tested datasets.
    This method can be activated via ``ssd.set_baseline_method('buffit')``.

    References
    ----------
    Implemented in molass-library issues #24 (buffit), #25 (Otsu threshold),
    and #26 (XrData default).
"""
import warnings

import numpy as np

BUFFIT_THRESHOLD = 0.10   # fraction of peak below which a frame is buffer


def _otsu_threshold(elution_norm, bins=100):
    """Return the Otsu threshold for a normalised elution curve.

    Finds the split point that maximises between-class variance of the
    values in *elution_norm*, which is assumed to be in [0, 1].

    Parameters
    ----------
    elution_norm : ndarray
        Normalised elution sum (``M.sum(axis=0) / M.sum(axis=0).max()``).
    bins : int, optional
        Number of histogram bins. Default is 100.

    Returns
    -------
    threshold : float
        Otsu threshold in the same units as *elution_norm*.

    References
    ----------
    N. Otsu, "A Threshold Selection Method from Gray-Level Histograms,"
    *IEEE Transactions on Systems, Man, and Cybernetics*, vol. 9, no. 1,
    pp. 62–66, 1979. https://doi.org/10.1109/TSMC.1979.4310076
    """
    counts, edges = np.histogram(elution_norm, bins=bins, range=(0.0, 1.0))
    centers = (edges[:-1] + edges[1:]) / 2
    total = counts.sum()
    best_t, best_var = centers[0], -1.0
    for i in range(1, len(counts)):
        w0 = counts[:i].sum() / total
        w1 = counts[i:].sum() / total
        if w0 == 0 or w1 == 0:
            continue
        m0 = (counts[:i] * centers[:i]).sum() / counts[:i].sum()
        m1 = (counts[i:] * centers[i:]).sum() / counts[i:].sum()
        var = w0 * w1 * (m0 - m1) ** 2
        if var > best_var:
            best_var, best_t = var, centers[i]
    return best_t


def compute_buffit_baseline(x, y, return_also_params=False, **kwargs):
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
        Optional ``buffer_mask`` (bool array, shape == y.shape),
        pre-computed once from the summed elution by ``SsMatrixData``.
        If absent or fewer than 2 True entries, falls back to a full-frame
        linear fit.  Passing ``threshold`` without ``buffer_mask`` has no
        effect and raises a ``UserWarning``.

    Returns
    -------
    baseline : ndarray
    params : dict  (only if return_also_params is True)
        Keys: ``slope``, ``intercept``, ``n_buffer``.
    """
    buffer_mask = kwargs.get('buffer_mask', None)
    if buffer_mask is None and 'threshold' in kwargs:
        warnings.warn(
            "compute_buffit_baseline: 'threshold' was passed but 'buffer_mask' was not. "
            "'threshold' is ignored at the per-row level; compute buffer_mask from the "
            "full matrix M.sum(axis=0) and pass it explicitly.",
            UserWarning,
            stacklevel=2,
        )
    n_buffer_frames = int(buffer_mask.sum()) if buffer_mask is not None else 0
    if n_buffer_frames < 2:
        # Fallback: use all frames
        slope, intercept = np.polyfit(x, y, 1)
        n_buffer_frames = len(x)
    else:
        slope, intercept = np.polyfit(x[buffer_mask], y[buffer_mask], 1)

    baseline = x * slope + intercept
    if return_also_params:
        return baseline, dict(slope=slope, intercept=intercept, n_buffer=n_buffer_frames)
    return baseline
