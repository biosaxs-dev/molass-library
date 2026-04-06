"""
Peaks.EghPeeler

Sequential EGH (Exponentially-modified Gaussian Hybrid) peeling for
automatic peak recognition and component count estimation.

Algorithm:
    1. Find tallest remaining peak (argmax of smoothed residual)
    2. Fit EGH(H, mu, sigma, tau) via L-BFGS-B
    3. Check significance: area(fitted) / total_area >= min_area_frac
    4. Check shape: sigma >= min_sigma (reject noise spikes)
    5. Subtract fitted EGH from residual
    6. Repeat until no significant candidate remains

This replaces the legacy ``recognize_peaks`` (greedy sequential subtraction
with symmetric Gaussian initialization) from molass-legacy.
"""
import numpy as np
from scipy.optimize import minimize as sp_minimize
from scipy.signal import savgol_filter
from molass.SEC.Models.Simple import egh, gaussian

DEFAULT_MIN_AREA_FRAC = 0.02
DEFAULT_MIN_SIGMA = 3.0
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


def egh_peel(x, y, num_components=None, min_area_frac=DEFAULT_MIN_AREA_FRAC,
             min_sigma=DEFAULT_MIN_SIGMA, debug=False):
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

        # Fitting window: zero out far-away data
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

        # Shape guard
        if sigma_fit < min_sigma:
            if debug:
                print(f"  Step {step+1}: sigma={sigma_fit:.1f} < {min_sigma} -> noise spike, stop")
            break

        # Area significance (only when auto-detecting)
        if num_components is None:
            peak_area = _egh_area(x, H_fit, mu_fit, sigma_fit, tau_fit)
            area_frac = peak_area / total_area
            if area_frac < min_area_frac:
                if debug:
                    print(f"  Step {step+1}: area={area_frac*100:.1f}% < {min_area_frac*100:.0f}% -> stop")
                break

        # Accept this peak
        egh_fit = egh(x, H_fit, mu_fit, sigma_fit, tau_fit)
        residual = residual - egh_fit

        peak_list.append([H_fit, mu_fit, sigma_fit, tau_fit])

        if debug:
            print(f"  Step {step+1}: mu={mu_fit:.1f}, H={H_fit:.5f}, "
                  f"sigma={sigma_fit:.1f}, tau={tau_fit:.1f}")

    # Sort by retention time (ascending mu)
    peak_list.sort(key=lambda p: p[1])
    return peak_list
