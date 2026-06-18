"""
Recommend decomposition options based on automated peak detection.

This module is the backend for :meth:`SecSaxsData.recommend_decomposition_options`.
Keeping the logic here allows it to grow (multi-channel heuristics, per-sample
tuning, custom strategies) without cluttering the top-level data object.
"""
import numpy as np

# ---------------------------------------------------------------------------
# EGH-peeling-based peak counting
# ---------------------------------------------------------------------------

_EGH_OVERLAP_THRESHOLD = 1.3  # spacing / sigma_sum below this → EGH peaks merge into one cluster
                               #
                               # Physical meaning: SAMPLE3 contains a single heavily-overlapping
                               # species whose elution peak is split by EGH peeling into 3 sub-peaks
                               # (frames ≈156, 194, 206).  Those sub-peaks are NOT separate components —
                               # they are artefacts of the sequential-subtraction algorithm fitting a
                               # single asymmetric peak.  The cluster-merge step folds them back into
                               # one component, restoring ncomp=1.
                               #
                               # Calibration (SAMPLE1–4):
                               #   SAMPLE3 max pair ratio = 1.232  → merged  → ncomp = 1  ✓
                               #   SAMPLE1 min pair ratio = 1.376  → kept    → ncomp = 3  ✓
                               #   SAMPLE2 min pair ratio = 1.423  → kept    → ncomp = 3  ✓
                               # Safe window: (1.232, 1.376).  1.3 sits near the centre.

# ---------------------------------------------------------------------------
# Interparticle detection helpers (Guinier low-q suppression test)
# ---------------------------------------------------------------------------

_LOWQ_SUPPRESSION_THRESHOLD = 0.995   # ratio < this → repulsive interparticle
_PEAK_FRAMES_THRESHOLD      = 0.1     # fraction of max integrated intensity
_GUINIER_Q_MAX_RATIO        = 1.3     # q·Rg upper bound for Guinier fit


def _peak_frames_matrix(M, threshold=_PEAK_FRAMES_THRESHOLD):
    """Return M restricted to frames where ∑_q I(q,j) > threshold × max.

    Excludes buffer (non-peak) frames.  After baseline correction those frames
    carry near-zero signal and only add noise to the SVD.
    """
    icurve = M.sum(axis=0)
    return M[:, icurve > threshold * icurve.max()]


def _guinier_func(q2, lnI0, Rg2):
    """Linearised Guinier model: ln I = ln I₀ − Rg² q² / 3."""
    return lnI0 - Rg2 * q2 / 3.0


def _low_q_suppression_ratio(qv, P1, guinier_q_max_ratio=_GUINIER_Q_MAX_RATIO):
    """Ratio P(q_min) / P_Guinier(q_min) for the leading SVD scattering profile.

    Fits the Guinier model iteratively in the region q·Rg < *guinier_q_max_ratio*,
    then compares the observed value at the lowest measured q to the extrapolation.

    Returns
    -------
    ratio : float
        < 1 → low-q suppression → repulsive interparticle effects present.
        > 1 → no suppression → clean sample.
        nan → fit failed (too few positive points or convergence error).
    Rg : float
        Fitted radius of gyration in the same units as ``qv`` (Å⁻¹ → Å).
    fit_ok : bool
    """
    from scipy.optimize import curve_fit

    # SVD eigenvectors have arbitrary sign; scattering profiles must be positive.
    if P1.mean() < 0:
        P1 = -P1

    pos = P1 > 0
    if pos.sum() < 10:
        return float('nan'), float('nan'), False

    qv_p, P1_p = qv[pos], P1[pos]
    lnP = np.log(P1_p)
    q2  = qv_p ** 2

    # Rough Rg estimate from linear Guinier fit over first 10 points.
    slope, _ = np.polyfit(q2[:10], lnP[:10], 1)
    Rg_init = np.sqrt(max(-3.0 * slope, 0.01))

    # Iterate: update Guinier window using current Rg estimate.
    popt = None
    for _ in range(5):
        mask = qv_p * Rg_init < guinier_q_max_ratio
        if mask.sum() < 4:
            return float('nan'), float('nan'), False
        try:
            popt, _ = curve_fit(_guinier_func, q2[mask], lnP[mask],
                                p0=[lnP[0], Rg_init ** 2], maxfev=2000)
        except RuntimeError:
            return float('nan'), float('nan'), False
        Rg_new = np.sqrt(max(popt[1], 0.0))
        if abs(Rg_new - Rg_init) < 0.01:
            break
        Rg_init = Rg_new

    if popt is None:
        return float('nan'), float('nan'), False

    lnI0, Rg2 = popt
    Rg = np.sqrt(max(Rg2, 0.0))
    q_min = qv_p[0]
    P_guinier = np.exp(_guinier_func(q_min ** 2, lnI0, Rg2))
    ratio = float(P1_p[0] / P_guinier)
    return ratio, Rg, True


def _has_interparticle_effects(xr_data,
                               suppression_threshold=_LOWQ_SUPPRESSION_THRESHOLD,
                               peak_frames_threshold=_PEAK_FRAMES_THRESHOLD):
    """Return True if low-q Guinier suppression indicates repulsive interparticle effects.

    Uses peak frames only (buffer frames excluded from SVD).
    Falls back to False on any fit failure (conservative: do not flag as interparticle
    unless the evidence is clear).
    """
    M      = xr_data.M
    qv     = xr_data.q_values
    M_peak = _peak_frames_matrix(M, peak_frames_threshold)
    if M_peak.shape[1] < 4:
        return False

    U, s, _ = np.linalg.svd(M_peak, full_matrices=False)
    P1 = U[:, 0] * s[0]

    ratio, _, ok = _low_q_suppression_ratio(qv, P1)
    if not ok or np.isnan(ratio):
        return False
    return ratio < suppression_threshold


# ---------------------------------------------------------------------------
# EGH-peeling-based component counting (replaces detect_peaks)
# ---------------------------------------------------------------------------

def _count_components_by_egh_peeling(xr_data,
                                      egh_overlap_threshold=_EGH_OVERLAP_THRESHOLD):
    """Count elution components via EGH peeling + cluster-merge.

    Returns
    -------
    num_components : int
    peak_positions : np.ndarray of int  (absolute frame numbers, one per cluster)
    is_overlapping : bool  (True if any cluster contains >1 EGH peak)
    """
    from molass.Peaks.EghPeeler import egh_peel

    x = xr_data.frame_indices.astype(float)
    y = xr_data.M.sum(axis=0)
    peak_list = egh_peel(x, y)

    if not peak_list:
        return 2, None, True          # fallback: 2-comp proportional

    peak_list = sorted(peak_list, key=lambda p: p[1])  # sort by mu

    if len(peak_list) == 1:
        return 1, np.array([int(round(peak_list[0][1]))]), False

    mus     = np.array([p[1] for p in peak_list])
    sigmas  = np.array([p[2] for p in peak_list])
    heights = np.array([p[0] for p in peak_list])

    ratios = np.diff(mus) / (sigmas[:-1] + sigmas[1:])  # spacing / sigma_sum

    # Group consecutive peaks whose spacing/sigma_sum < threshold into one cluster.
    clusters = [[0]]
    for i, r in enumerate(ratios):
        if r < egh_overlap_threshold:
            clusters[-1].append(i + 1)
        else:
            clusters.append([i + 1])

    # Each cluster → one component at the position of its tallest peak.
    peak_positions = np.array([
        int(round(mus[max(c, key=lambda i: heights[i])]))
        for c in clusters
    ])
    is_overlapping = any(len(c) > 1 for c in clusters)
    return len(clusters), peak_positions, is_overlapping


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recommend_decomposition_options(xr_data,
                                    detect_interparticle=True,
                                    lowq_suppression_threshold=_LOWQ_SUPPRESSION_THRESHOLD,
                                    egh_overlap_threshold=_EGH_OVERLAP_THRESHOLD):
    """Recommend keyword arguments for ``quick_decomposition()`` by detecting peaks.

    Uses EGH peeling to identify elution components robustly.  Consecutive
    EGH peaks whose spacing/sigma_sum ratio falls below *egh_overlap_threshold*
    are merged into a single component (the one at the tallest peak position
    in that cluster).

    Parameters
    ----------
    xr_data : XrData
        The X-ray scattering data channel of a corrected ``SecSaxsData``.
    detect_interparticle : bool, optional
        If True (default), test for repulsive interparticle effects via the
        Guinier low-q suppression criterion.  When detected, ``ranks=[2]``
        is added to the returned options so that ``optimize_rigorously()``
        uses a rank-2 component model.
    lowq_suppression_threshold : float, optional
        The Guinier suppression ratio below which interparticle effects are
        flagged.  Default 0.995 (requires ≥0.5 % suppression at q_min).
    egh_overlap_threshold : float, optional
        EGH peak pairs with spacing/sigma_sum below this value are merged
        into one component.  Default 1.3.
        Validated on SAMPLE1–4: safe window is (1.232, 1.376).

    Returns
    -------
    dict
        Keyword arguments ready to pass to ``quick_decomposition()``:

        - ``{'num_components': n, 'xr_peakpositions': peaks}``
          when all clusters are single EGH peaks (well-separated).
        - ``{'num_components': n, 'proportions': [1]*n}``
          when any cluster was formed by merging overlapping EGH peaks.
        - ``{'num_components': 2, 'proportions': [1, 1]}``
          as a fallback when EGH peeling finds no peaks.

        Additionally, ``'ranks': [2, ...]`` is included when repulsive
        interparticle effects are detected via the Guinier low-q test.
    """
    n, peak_positions, is_overlapping = _count_components_by_egh_peeling(
        xr_data, egh_overlap_threshold=egh_overlap_threshold)

    if peak_positions is None:
        return {'num_components': 2, 'proportions': [1, 1]}

    if is_overlapping:
        opts = {'num_components': n, 'proportions': [1] * n}
    else:
        opts = {'num_components': n, 'xr_peakpositions': peak_positions}

    if detect_interparticle and _has_interparticle_effects(
            xr_data, suppression_threshold=lowq_suppression_threshold):
        opts['ranks'] = [2] * n

    return opts
