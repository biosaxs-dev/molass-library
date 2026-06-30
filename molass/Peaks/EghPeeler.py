"""
Peaks.EghPeeler

Sequential EGH (Exponentially-modified Gaussian Hybrid) peeling for
automatic peak recognition and component count estimation.

Algorithm:
    1. Find tallest remaining peak (argmax of smoothed residual)
    2. Fit EGH(H, mu, sigma, tau) via L-BFGS-B
    3. Check shape: min_sigma <= sigma <= max_sigma (see below)
    4. Check significance: area(fitted) / total_area >= min_area_frac
    5. Subtract fitted EGH from residual
    6. Repeat until no significant candidate remains

Physical basis for max_sigma_ratio
----------------------------------
The theoretical plate number N = (tR / sigma)^2 is a column property,
approximately constant across all peaks in the same run.  This means
sigma = tR / sqrt(N), i.e. sigma is proportional to retention time tR.

Our data is in frame space, where frame numbers do not start from
injection.  However, the unknown offset f_offset >= 0, so the most
permissive bound (f_offset = 0) gives:

    sigma_k / sigma_1 <= mu_k / mu_1

Since all peaks lie in a narrow frame window, mu_k / mu_1 ~ 1,
and any positive f_offset only tightens the bound.  Therefore all
real peaks must have sigma within a small multiple of the dominant
peak's sigma.  The default ratio of 2.0 includes a generous safety
margin; empirically, legitimate peaks fall within 1.5x.

Reference:
    https://www.shimadzu.com/an/service-support/technical-support/
    analysis-basics/basic/theoretical_plate.html

This replaces the legacy ``recognize_peaks`` (greedy sequential subtraction
with symmetric Gaussian initialization) from molass-legacy.
"""
import numpy as np
from scipy.optimize import minimize as sp_minimize
from scipy.signal import savgol_filter
from molass.SEC.Models.Simple import egh, gaussian

DEFAULT_MIN_AREA_FRAC = 0.02
DEFAULT_MIN_HEIGHT_FRAC = 0.05
DEFAULT_MIN_SIGMA = 3.0
DEFAULT_MAX_SIGMA_RATIO = 2.0
TAU_BOUND_RATIO = 2.0
MAX_STEPS = 10


def _egh_area(x, H, mu, sigma, tau):
    """Compute area under an EGH peak by numerical integration."""
    y = egh(x, H, mu, sigma, tau)
    return np.trapezoid(y, x)


def _estimate_sigma(x, y, peak_idx, h_init, mu_init):
    """Estimate initial sigma by expanding a Gaussian window until >50% of
    points fall below the Gaussian envelope."""
    sigma_init = 5.0
    for s in range(3, len(x) // 2):
        sl = slice(max(0, peak_idx - s), min(len(x), peak_idx + s))
        gy = gaussian(x[sl], h_init, mu_init, s)
        neg_frac = np.sum(y[sl] - gy < 0) / len(x[sl])
        if neg_frac > 0.5:
            sigma_init = float(s)
            break
    return sigma_init


def _estimate_tau(x, y, peak_idx):
    """Estimate initial tau from asymmetry of the peak at half-maximum.

    Compares the half-width on the left vs right side of the peak.
    A right-tailing peak (common in SEC) yields tau > 0.
    Returns 0.0 for symmetric or fronting peaks.
    """
    h_peak = y[peak_idx]
    if h_peak <= 0:
        return 0.0
    half_h = h_peak / 2.0

    # Find half-max crossing on the left
    left_x = None
    for i in range(peak_idx, 0, -1):
        if y[i] < half_h:
            dy = y[i + 1] - y[i]
            frac = (half_h - y[i]) / dy if dy != 0 else 0
            left_x = x[i] + frac * (x[i + 1] - x[i])
            break

    # Find half-max crossing on the right
    right_x = None
    for i in range(peak_idx, len(y) - 1):
        if y[i] < half_h:
            dy = y[i - 1] - y[i]
            frac = (half_h - y[i]) / dy if dy != 0 else 0
            right_x = x[i] - frac * (x[i] - x[i - 1])
            break

    if left_x is None or right_x is None:
        return 0.0

    w_left = x[peak_idx] - left_x
    w_right = right_x - x[peak_idx]

    # tau is roughly proportional to the half-width difference
    return max(0.0, w_right - w_left)


def egh_peel(x, y, num_components=None, min_area_frac=DEFAULT_MIN_AREA_FRAC,
             min_sigma=DEFAULT_MIN_SIGMA, max_sigma_ratio=DEFAULT_MAX_SIGMA_RATIO,
             min_height_frac=DEFAULT_MIN_HEIGHT_FRAC,
             debug=False):
    """Sequential EGH peeling to find peaks and estimate component count.

    Parameters
    ----------
    x : array-like
        Frame positions (1-D).
    y : array-like
        Intensity values (1-D, same length as *x*).
    num_components : int or None
        If given, peel exactly this many peaks (ignoring area significance).
        If ``None``, peel until no significant candidate remains.
    min_area_frac : float
        Minimum area fraction (relative to total curve area) for a peak to
        be considered significant.  Only used when ``num_components is None``.
        Default 0.02 (2 %).
    min_sigma : float
        Minimum allowed sigma.  Peaks narrower than this are rejected as
        noise spikes.  Default 3.0 frames.
    max_sigma_ratio : float or None
        Maximum allowed sigma as a multiple of the first (dominant) peak's
        sigma.  Peaks wider than ``max_sigma_ratio * sigma_dominant`` are
        rejected as physically implausible (plate number constraint).
        Default 2.0.  Set to ``None`` to disable.
    min_height_frac : float
        Minimum allowed height as a fraction of the dominant peak's height.
        Candidate peaks shorter than ``min_height_frac * H_dominant`` are
        rejected as ghost components.  Only used when
        ``num_components is None``.  Default 0.05 (5 %).
    debug : bool
        If True, print diagnostic messages.

    Returns
    -------
    peak_list : list of list
        Each element is ``[H, mu, sigma, tau]`` — the fitted EGH parameters.
        Sorted by ascending *mu* (retention time order).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    residual = y.copy()
    residual[residual < 0] = 0

    total_area = np.trapezoid(y, x)
    if total_area <= 0:
        return []

    max_steps = num_components if num_components is not None else MAX_STEPS
    peak_list = []
    sigma_dominant = None

    for step in range(max_steps):
        # Smooth residual to avoid fitting noise spikes
        win = min(31, max(5, len(residual) // 8 * 2 + 1))
        smooth = savgol_filter(residual, win, 3)
        smooth[smooth < 0] = 0
        peak_idx = np.argmax(smooth)
        peak_height = smooth[peak_idx]

        if peak_height <= 0:
            if debug:
                print(f"  Step {step+1}: residual is flat -> stop")
            break

        mu_init = x[peak_idx]
        h_init = residual[peak_idx]
        if h_init <= 0:
            h_init = peak_height

        sigma_init = _estimate_sigma(x, residual, peak_idx, h_init, mu_init)

        # Fitting window: ±3σ covers the Gaussian core.
        # The full-range objective (below) penalizes model signal outside this
        # window, which suppresses tau toward zero. This is intentional:
        # conservative (near-Gaussian) subtraction preserves residual signal
        # for subsequent peaks, improving detection robustness.
        # The downstream joint optimizer (CurveDecomposer) estimates accurate
        # tau values from the full multi-peak model.
        width = int(sigma_init * 3)
        left = max(0, peak_idx - width)
        right = min(len(x), peak_idx + width)
        y_for_fit = residual.copy()
        y_for_fit[:left] = 0
        y_for_fit[right:] = 0
        y_for_fit[y_for_fit < 0] = 0

        max_width = x[-1] - x[0]
        h_upper = max(h_init * 1.5, 1e-10)
        bounds = [(0, h_upper), (x[0], x[-1]),
                  (1, max_width), (0, max_width)]

        def objective(p):
            H, mu, sigma, tau = p
            model_y = egh(x, H, mu, sigma, tau)
            data_fit = np.sum((model_y - y_for_fit) ** 2)
            penalty = 1e3 * max(0, tau - sigma * TAU_BOUND_RATIO) ** 2
            return data_fit + penalty

        result = sp_minimize(objective, [h_init, mu_init, sigma_init, 0.0],
                             bounds=bounds, method='L-BFGS-B')
        H_fit, mu_fit, sigma_fit, tau_fit = result.x

        # Shape guard: too narrow
        if sigma_fit < min_sigma:
            if debug:
                print(f"  Step {step+1}: sigma={sigma_fit:.1f} < {min_sigma} -> noise spike, stop")
            break

        # Shape guard: too wide (see "Physical basis" in module docstring)
        if max_sigma_ratio is not None and sigma_dominant is not None:
            max_sigma = sigma_dominant * max_sigma_ratio
            if sigma_fit > max_sigma:
                if debug:
                    print(f"  Step {step+1}: sigma={sigma_fit:.1f} > {max_sigma:.1f} "
                          f"({max_sigma_ratio}×σ₁) -> too wide, stop")
                break

        # Area and height significance (only when auto-detecting)
        if num_components is None:
            # Height significance: reject ghost components
            if len(peak_list) > 0:
                height_ratio = H_fit / peak_list[0][0]
                if height_ratio < min_height_frac:
                    if debug:
                        print(f"  Step {step+1}: height={H_fit:.5f} is {height_ratio:.1%} "
                              f"of dominant ({min_height_frac:.0%} required) -> ghost, stop")
                    break

            peak_area = _egh_area(x, H_fit, mu_fit, sigma_fit, tau_fit)
            area_frac = peak_area / total_area
            if area_frac < min_area_frac:
                if debug:
                    print(f"  Step {step+1}: area={area_frac*100:.1f}% < {min_area_frac*100:.0f}% -> stop")
                break

        # Accept this peak
        egh_fit = egh(x, H_fit, mu_fit, sigma_fit, tau_fit)
        residual = residual - egh_fit

        if sigma_dominant is None:
            sigma_dominant = sigma_fit

        peak_list.append([H_fit, mu_fit, sigma_fit, tau_fit])

        if debug:
            print(f"  Step {step+1}: mu={mu_fit:.1f}, H={H_fit:.5f}, "
                  f"sigma={sigma_fit:.1f}, tau={tau_fit:.1f}")

    # Sort by retention time (ascending mu)
    peak_list.sort(key=lambda p: p[1])
    return peak_list
