"""
    Continuity.Indicators.py

    Array-level indicators behind the continuity report (molass-library#370): they take plain
    arrays, return plain numbers and know nothing about decompositions, so they can be reused
    on their own (for example in a simulation).

    Origin: molass-researcher experiments 51i-51r (``experiments/51_paper_m_results``).
"""
from itertools import combinations
import numpy as np
from scipy.signal import savgol_filter

KRATKY_QRG_RANGE = (0.5, 5.0)   # qRg range in which the Kratky curves are compared
_KRATKY_GRID_SIZE = 200


def rg_point_noise(frames, rgs):
    """Robust standard deviation of a single Rg value, from the differences of neighbouring frames.

    Only pairs of consecutive frames are used, so gaps (frames removed by the reliability
    filter) do not inflate the estimate. Returns NaN with fewer than two such pairs.
    """
    frames = np.asarray(frames, dtype=float)
    rgs = np.asarray(rgs, dtype=float)
    d = np.diff(rgs)[np.diff(frames) == 1]
    if len(d) < 2:
        return np.nan
    return float(1.4826*np.median(np.abs(d - np.median(d)))/np.sqrt(2))


def rg_drop(rgs, k=5):
    """Total drop of an Rg curve: |median of the first ``k`` - median of the last ``k`` values|."""
    rgs = np.asarray(rgs, dtype=float)
    k = max(1, min(k, len(rgs)//2))
    return float(abs(np.median(rgs[:k]) - np.median(rgs[-k:])))


def longest_constant_run(frames, rgs, sigma, tol=1.5, nmin=5, lo=0, hi=None):
    """Longest run of points ``lo..hi-1`` that a constant fits within the noise.

    A run qualifies when the residual sum of squares of its constant fit is at most
    ``tol*(n - 1)*sigma**2``. Its length is measured in frames (``frames[j-1] - frames[i] + 1``).

    Returns
    -------
    tuple
        ``(span, i, j)``: the length in frames and the point range ``i..j-1``;
        ``(0, lo, lo)`` if there is none.
    """
    frames = np.asarray(frames, dtype=float)
    y = np.asarray(rgs, dtype=float)
    hi = len(y) if hi is None else hi
    c1 = np.concatenate([[0.0], np.cumsum(y)])
    c2 = np.concatenate([[0.0], np.cumsum(y**2)])
    best = (0, lo, lo)
    for i in range(lo, hi - nmin + 1):
        j = np.arange(i + nmin, hi + 1)
        s = c1[j] - c1[i]
        rss = c2[j] - c2[i] - s*s/(j - i)
        ok = rss <= tol*(j - i - 1)*sigma**2
        if not ok.any():
            continue
        span = frames[j[ok] - 1] - frames[i] + 1
        m = int(np.argmax(span))
        if span[m] > best[0]:
            best = (float(span[m]), i, int(j[ok][m]))
    return best


def ramp_run_length(frames, rgs, sigma, tol=1.5):
    """Longest constant-within-noise run (in frames) to be expected if the overall Rg drop were a
    uniform ramp: ``sqrt(12*tol)*sigma/slope``. ``inf`` for a curve without a net drop."""
    frames = np.asarray(frames, dtype=float)
    y = np.asarray(rgs, dtype=float)
    k = max(3, min(10, len(y)//4))
    drop = abs(np.median(y[:k]) - np.median(y[-k:]))
    span = np.median(frames[-k:]) - np.median(frames[:k])
    slope = drop/span if span > 0 else 0.0
    return float(np.sqrt(12*tol)*sigma/slope) if slope > 0 else np.inf


def plateau_excess(frames, rgs, tol=1.5, sigma=None):
    """Plateau excess of an Rg curve: its longest constant-within-noise run divided by the run a
    uniform ramp of the same drop would allow.

    A single species has the same Rg at every concentration, so a mixture of discrete species
    shows plateaus; a continuum shows a ramp. Values above 1 mean "flatter than a ramp"; ramps
    give about 0.9-1.2 and clear staircases 2-3 (molass-researcher 51m, 51o). It is blind when the
    drop is small against the noise and depends on the noise and the curvature of the ramp.
    NaN if the noise cannot be estimated.
    """
    sigma = rg_point_noise(frames, rgs) if sigma is None else sigma
    if not np.isfinite(sigma) or sigma <= 0:
        return np.nan
    return float(longest_constant_run(frames, rgs, sigma, tol)[0]/ramp_run_length(frames, rgs, sigma, tol))


def find_plateaus(frames, rgs, sigma=None, tol=1.5, min_excess=1.5, min_frames=10):
    """All non-overlapping plateaus of an Rg curve, found longest first (recursively on both sides).

    A plateau must be at least ``min_frames`` long and ``min_excess`` times the ramp run length.

    Returns
    -------
    list of dict
        ``start``, ``stop`` (frames), ``length`` (frames) and ``level`` (mean Rg), in frame order.
    """
    frames = np.asarray(frames, dtype=float)
    y = np.asarray(rgs, dtype=float)
    sigma = rg_point_noise(frames, y) if sigma is None else sigma
    if not np.isfinite(sigma) or sigma <= 0:
        return []
    lnull = ramp_run_length(frames, y, sigma, tol)
    found = []

    def rec(lo, hi):
        if hi - lo < 5:
            return
        span, i, j = longest_constant_run(frames, y, sigma, tol, lo=lo, hi=hi)
        if span >= max(min_frames, min_excess*lnull):
            found.append(dict(start=float(frames[i]), stop=float(frames[j-1]), length=float(span),
                              level=float(y[i:j].mean())))
            rec(lo, i)
            rec(j, hi)

    rec(0, len(y))
    return sorted(found, key=lambda p: p["start"])


def _smooth(ky, window=15, polyorder=3):
    n = len(ky)
    w = min(window, n - (1 - n % 2))
    if w < polyorder + 2:
        return np.asarray(ky, dtype=float)
    return savgol_filter(ky, w, polyorder)


def kratky_separation(curves, qrg_range=KRATKY_QRG_RANGE):
    """Pairwise differences of the dimensionless Kratky curves of the components, in noise units.

    Parameters
    ----------
    curves : list of (qrg, ky) or None
        Per component the Kratky curve as in ``ShapeMatchResult.kratky_curves``
        (``qrg`` increasing). Entries that are ``None`` are skipped.
    qrg_range : tuple of float
        The qRg range of the comparison.

    Returns
    -------
    dict
        ``sep`` (matrix of RMS differences divided by the combined noise of the two curves),
        ``max_sep`` (largest entry), ``end_fraction`` (separation of the first and the last
        component divided by ``max_sep``: 1 when the ends of the elution are the most different,
        i.e. the components form a series ordered along the elution) and ``sigma`` (noise of each
        curve). ``max_sep`` is NaN with fewer than two usable curves.

    Notes
    -----
    ``max_sep`` measures how different the *shapes* are, not whether species are discrete: a wide
    continuum has a large one, and two different compact proteins a small one (51k, 51n, 51o).
    """
    curves = [c for c in curves if c is not None]
    if len(curves) < 2:
        return dict(sep=np.zeros((len(curves), len(curves))), max_sep=np.nan, end_fraction=np.nan,
                    sigma=np.full(len(curves), np.nan))
    grid = np.linspace(qrg_range[0], qrg_range[1], _KRATKY_GRID_SIZE)
    smoothed, sigma = [], []
    for qrg, ky in curves:
        qrg, ky = np.asarray(qrg, dtype=float), np.asarray(ky, dtype=float)
        sm = _smooth(ky)
        m = (qrg >= qrg_range[0]) & (qrg <= qrg_range[1])
        sigma.append(1.4826*np.median(np.abs((ky - sm)[m])) if m.any() else np.nan)
        smoothed.append(np.interp(grid, qrg, sm))
    sigma = np.array(sigma)
    n = len(curves)
    sep = np.zeros((n, n))
    for i, j in combinations(range(n), 2):
        rms = np.sqrt(np.mean((smoothed[i] - smoothed[j])**2))
        sep[i, j] = sep[j, i] = rms/np.hypot(sigma[i], sigma[j])
    max_sep = float(np.nanmax(sep))
    end_fraction = float(sep[0, -1]/max_sep) if max_sep > 0 else np.nan
    return dict(sep=sep, max_sep=max_sep, end_fraction=end_fraction, sigma=sigma)
