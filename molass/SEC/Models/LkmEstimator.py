"""
SEC.Models.LkmEstimator.py

Estimate LKM (Lumped Kinetic Model) initial parameters from EGH component moments.

The moment-matching approach follows the same design as SdmEstimator:
  1. Compute numerical moments (M1, M2, M3) from each EGH component curve.
  2. Match these to the LKM analytical cumulant expressions.

LKM analytical cumulants (per component; Pe and t0 are shared across components):

    kappa1_i = t0 * R_i                                                  (mean = tR_i)
    kappa2_i = 2*tR_i**2/Pe + 2*t0*(R_i-1)/k_MT_i                      (variance)
    kappa3_i = 12*tR_i**3/Pe**2
               + 12*tR_i*t0*(R_i-1)/(Pe*k_MT_i)
               + 6*t0*(R_i-1)/k_MT_i**2                                  (third cumulant)

Factored optimization:
    Given (t0, Pe), R_i = tR_i/t0 is determined, and k_MT_i can be solved
    analytically from the kappa2_i equation.  The outer optimization over (t0, Pe)
    then minimises the kappa3 residuals.

    This construction guarantees that kappa1 and kappa2 are matched exactly by
    the returned parameters; kappa3 is matched as closely as possible.

In the large-Pe limit the factored solution reduces to the closed-form
three-moment formulas:

    k_MT_i  ≈  3 * M2_i / M3_i
    t0      ≈  M1_i - 3 * M2_i**2 / (2 * M3_i)
    R_i     =  M1_i / t0

which are derived from the compound-Poisson characteristic function of the
kinetics-only model (see molass-essence/chapters/45/characteristic-function.ipynb).
"""

import numpy as np
from scipy.optimize import minimize

# ── Constants ────────────────────────────────────────────────────────────────
K_MT_MAX = 5000.0    # clamp when kinetics term is negligible (Pe-dominated peak)
PE_MIN   = 10.0
PE_MAX   = 20000.0   # cap at physically reasonable SEC range; BH can explore higher
T0_FRAC  = 0.98      # t0 must be < T0_FRAC * min(tR)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _compute_data_moments(xr_ccurves):
    """
    Compute (M1, M2, M3, scale) from each EGH component curve.

    Uses discrete weighted sums (same convention as SdmEstimator).
    """
    moment_list = []
    for ccurve in xr_ccurves:
        cx, cy = ccurve.get_xy()
        y_pos  = np.maximum(cy, 0)
        W      = y_pos.sum()
        m1     = (cx * y_pos).sum() / W
        m2c    = (y_pos * (cx - m1)**2).sum() / W
        m3c    = (y_pos * (cx - m1)**3).sum() / W
        scale  = np.trapezoid(y_pos, cx)
        moment_list.append((m1, m2c, m3c, scale))
    return moment_list


def _lkm_kappa3(t0, Pe, R, k_MT):
    tR = t0 * R
    return (12 * tR**3 / Pe**2
            + 12 * tR * t0 * (R - 1) / (Pe * k_MT)
            + 6  * t0 * (R - 1) / k_MT**2)


def _k_MT_from_kappa2(t0, Pe, tR, kappa2):
    """
    Solve k_MT analytically from the kappa2 equation.

    kappa2 = 2*tR**2/Pe  +  2*t0*(R-1)/k_MT
    =>  k_MT = 2*t0*(R-1) / (kappa2 - 2*tR**2/Pe)

    Returns K_MT_MAX when the kinetics term is negligible (Pe-dominated peak).
    """
    dispersion_var = 2 * tR**2 / Pe
    kinetics_var   = kappa2 - dispersion_var
    if kinetics_var <= 0:
        return K_MT_MAX                  # all broadening from dispersion
    R    = tR / t0
    k_MT = 2 * t0 * (R - 1) / kinetics_var
    return float(np.clip(k_MT, 0.01, K_MT_MAX))


def _initial_t0_guess(moment_list):
    """
    Estimate t0 using the large-Pe three-moment formula.

    Tries all components and returns the smallest valid estimate,
    which maximises the retention factor R and gives the most headroom
    for the outer optimisation.  Falls back to tR_min / 3.0 when no
    component yields a valid three-moment t0 (e.g. nearly-excluded
    proteins where M3 ≈ 0).
    """
    tR_min   = min(m[0] for m in moment_list)
    t0_upper = T0_FRAC * tR_min

    valid_t0s = []
    for m1, m2c, m3c, _ in moment_list:
        if m3c > 1e-6 * m2c**1.5:          # positive skew and reasonable M3
            t0_est = m1 - 3 * m2c**2 / (2 * m3c)
            if 1.0 < t0_est < t0_upper:
                valid_t0s.append(t0_est)

    if valid_t0s:
        return min(valid_t0s)               # smallest t0 → largest R → most headroom

    # Fallback: assume R ≈ 3 for a typical SEC column
    return tR_min / 3.0


# ── Public API ───────────────────────────────────────────────────────────────

def estimate_lkm_init_params(decomposition, **kwargs):
    """
    Estimate LKM initial parameters from EGH component moments.

    Follows the same *upgrade* design as :func:`estimate_sdm_column_params`:
    numerical moments are computed from each EGH component curve
    (via :meth:`ComponentCurve.get_xy`) and matched to the LKM analytical
    cumulant expressions.

    Parameters
    ----------
    decomposition : Decomposition
        Decomposition whose ``xr_ccurves`` hold the EGH component curves.
    debug : bool, optional
        If True, print diagnostics (default False).

    Returns
    -------
    Pe : float
        Péclet number (shared column parameter).
    t0 : float
        Dead time in frame units (shared column parameter).
    k_MT_list : list of float
        Mass-transfer rate per component (same units as frame axis).
    R_list : list of float
        Retention factor per component (R_i = tR_i / t0 ≥ 1).
    scale_list : list of float
        Area scale per component (integral of EGH component curve).

    Notes
    -----
    The optimisation is factored:

    * *Inner* (analytic): for a given (t0, Pe), k_MT_i is solved exactly from
      the kappa2 equation, guaranteeing kappa1 and kappa2 are matched.
    * *Outer* (numeric, 2-D): L-BFGS-B over log(t0) and log(Pe) minimises the
      kappa3 residuals (sign-preserving cube roots, same as SdmEstimator).

    In the large-Pe limit the result converges to the closed-form
    three-moment formulas derived from the compound-Poisson CF.
    """
    debug     = kwargs.get('debug', False)
    xr_ccurves = decomposition.xr_ccurves
    moment_list = _compute_data_moments(xr_ccurves)

    tR_list = [m[0] for m in moment_list]
    tR_min  = min(tR_list)

    # ── Initial guess ─────────────────────────────────────────────────────────
    t0_0 = _initial_t0_guess(moment_list)

    # Upper-bound Pe estimate from the largest component (ignoring kinetics)
    largest_idx = max(range(len(moment_list)), key=lambda i: moment_list[i][3])
    m1_d, m2c_d, _, _ = moment_list[largest_idx]
    Pe_0 = float(np.clip(2 * m1_d**2 / m2c_d, PE_MIN, PE_MAX))

    if debug:
        print(f"Initial guess: t0={t0_0:.2f}  Pe={Pe_0:.1f}")
        for i, (tR, m2c, m3c, scale) in enumerate(zip(tR_list, *zip(*[(m[1], m[2], m[3]) for m in moment_list]))):
            sk3 = np.sign(m3c) * abs(m3c)**(1/3)
            print(f"  comp {i+1}: tR={tR:.1f}  std={np.sqrt(m2c):.2f}  sk3={sk3:.3f}  scale={scale:.3f}")

    # ── Factored optimisation over (log t0, log Pe) ───────────────────────────
    def objective(log_params):
        t0 = np.exp(log_params[0])
        Pe = np.exp(log_params[1])

        if t0 >= T0_FRAC * tR_min:
            return 1e10

        err = 0.0
        for m1, m2c, m3c, _ in moment_list:
            tR = m1
            R  = tR / t0
            if R <= 1.0:
                return 1e10

            # Feasibility: the axial-dispersion term alone must not exceed
            # the measured kappa2.  If it does, Pe is too small.
            if 2.0 * tR**2 / Pe >= m2c:
                return 1e10

            k_MT         = _k_MT_from_kappa2(t0, Pe, tR, m2c)
            kappa3_model = _lkm_kappa3(t0, Pe, R, k_MT)
            sk3_data     = np.sign(m3c) * abs(m3c)**(1/3)
            sk3_model    = np.sign(kappa3_model) * abs(kappa3_model)**(1/3)
            err += (sk3_data - sk3_model)**2

        return err

    x0     = [np.log(t0_0), np.log(Pe_0)]
    bounds = [
        (np.log(1.0),                   np.log(T0_FRAC * tR_min)),
        (np.log(PE_MIN),                np.log(PE_MAX)),
    ]

    result = minimize(objective, x0, method='L-BFGS-B', bounds=bounds,
                      options={'maxiter': 2000, 'ftol': 1e-12})

    t0_opt = float(np.exp(result.x[0]))
    Pe_opt = float(np.exp(result.x[1]))

    # ── Collect per-component outputs ─────────────────────────────────────────
    k_MT_list  = []
    R_list     = []
    scale_list = []

    for m1, m2c, m3c, scale in moment_list:
        tR   = m1
        R    = tR / t0_opt
        k_MT = _k_MT_from_kappa2(t0_opt, Pe_opt, tR, m2c)
        k_MT_list.append(k_MT)
        R_list.append(R)
        scale_list.append(scale)

    if debug:
        print(f"\nOptimised: t0={t0_opt:.2f}  Pe={Pe_opt:.1f}  (fun={result.fun:.4e})")
        for i, (tR, R, k_MT) in enumerate(zip(tR_list, R_list, k_MT_list)):
            print(f"  comp {i+1}: tR={tR:.1f}  R={R:.3f}  k_MT={k_MT:.4f}")

    return Pe_opt, t0_opt, k_MT_list, R_list, scale_list
