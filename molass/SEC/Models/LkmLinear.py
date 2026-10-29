"""
SEC.Models.LkmLinear.py

PDF of the Lumped Kinetic Model (LKM) with a **linear isotherm**, computed via
characteristic function (CF) inversion using FFT (PDE-based).

Assumptions
-----------
- Linear isotherm: q = a * c  (constant Henry coefficient; no overloading)
- Axial dispersion parametrised by the Peclet number Pe = u*L/D_ax
- Mass transfer between mobile and stationary phases follows a linear driving
  force with rate constant k_MT  (standard LKM convention: k_MT = k_STLC / (1-ε))

Model parameters
----------------
Pe    : Peclet number  Pe = u*L/D_ax
t0    : dead time  t0 = L/u  (mobile-phase transit time)
k_MT  : mass-transfer rate constant [1/time]
R     : retention factor  R = t_R / t0 = 1 + F*a  (F = (1-ε)/ε, a = Henry coeff.)

Transfer function (Laplace domain)
-----------------------------------
H(s) = exp( Pe/2 * (1 - sqrt(1 + 4*s*t0*(s + k_MT*R) / (Pe*(s + k_MT)))) )

References
----------
- Lapidus & Amundson (1952), J. Phys. Chem. 56:984
- Felinger et al. (2004), J. Chromatogr. A 1043:149–157 (SDM≡LKM equivalence)
- Validated against STLC PDE solver in molass-researcher/experiments/19_sdm_upgrade/19g, 19h
"""
import numpy as np
from molass.MathUtils.FftUtils import FftInvPdf


def lkm_linear_cf(w, Pe, t0_s, k_s, R):
    """
    Characteristic function of the LKM elution profile (scaled coordinates).

    Parameters are in **scaled** time units (see ``lkm_pdf`` for the scaling
    convention).  Do not call this directly; use ``lkm_pdf`` instead.
    """
    s   = -1j * w
    Phi = (4.0 / Pe) * s * t0_s * (s + k_s * R) / (s + k_s)
    return np.exp(0.5 * Pe * (1.0 - np.sqrt(1.0 + Phi)))


_lkm_pdf_impl = FftInvPdf(lkm_linear_cf)


def lkm_pdf(x, Pe, t0, k_MT, R, c_inj=1.0, t_inj=1.0, timescale=None):
    """
    PDF of the LKM (Lumped Kinetic Model) elution profile with linear isotherm.

    Uses FFT-based characteristic function inversion via
    :class:`~molass.MathUtils.FftUtils.FftInvPdf`.

    Parameters
    ----------
    x : array_like
        Time array (physical time units, e.g. seconds or minutes).
    Pe : float
        Peclet number  Pe = u*L/D_ax.  Controls axial dispersion width.
        Typical SEC range: 100–1000.
    t0 : float
        Dead time — mobile-phase transit time (same units as ``x``).
    k_MT : float
        Mass-transfer rate constant [1/time], **standard LKM convention**:
        ``dq/dt = k_MT × (a·c − q)``  (ε = mobile-phase porosity).

        Some LKM solvers normalise the rate internally by ``(1−ε)``.  For
        example, the `STLC <https://github.com/sartorius-research/STLC>`_
        package implements ``dq/dt = k/(1−ε) × (a·c − q)``, so its
        user-facing ``k`` differs from ``k_MT``.  Convert with
        ``k_MT = k_solver / (1 − ε)`` before passing to this function.
    R : float
        Retention factor  R = t_R / t0 = 1 + F*a
        (F = phase ratio = (1-ε)/ε, a = Henry coefficient).
    c_inj : float, optional
        Injection concentration — physical concentration of solute injected at
        the column inlet (units: mass/volume, e.g. g/L).
        Default: 1.0 (returns normalized curve).
    t_inj : float, optional
        Injection time — duration of the rectangular pulse injection
        (same time units as ``x`` and ``t0``).
        Default: 1.0 (returns normalized curve).
    timescale : float or None, optional
        Time rescaling factor for the internal FFT grid.
        If ``None`` (default), chosen automatically as ``80 / (t0 * R)``,
        mapping the peak position t_R = t0*R to position 80 on the
        FFT grid ``[0, 1024]``.
        Override if the default produces edge artefacts (e.g. very wide peaks).

    Returns
    -------
    ndarray
        LKM elution curve evaluated at each point in ``x``.
        The integral over ``x`` equals approximately ``c_inj × t_inj``
        (zeroth moment, see Qamar 2014, Andersson 2022).
        With default parameters (c_inj=1.0, t_inj=1.0), returns a normalized
        PDF (integral ≈ 1).

    Notes
    -----
    Linearity assumption
        This model assumes a **linear isotherm** (constant Henry coefficient a).
        At high sample loads the isotherm becomes non-linear (Langmuir or
        anti-Langmuir), invalidating R as a fixed parameter.  Use this model
        only in the linear (dilute) regime typical of analytical SEC-SAXS.

    Relationship to the D=0 (Thomas) model
        In the limit Pe → ∞ this CF reduces to the Thomas / kinetic model,
        which has a closed-form Bessel I₁ solution.  At typical SEC Peclet
        numbers (Pe ~ 100–500) the D=0 approximation introduces a systematic
        k_MT underestimation of ~3–4% (validated in experiment 19h).  This
        PDE-CF implementation avoids that bias.

    Equivalence to the stochastic–dispersive model (Felinger 2004)
        Felinger *et al.* (J. Chromatogr. A 1043:149–157, 2004) proved that
        the **LKM is mathematically identical to the stochastic–dispersive model
        (SDM)** in linear chromatography, provided exponential sojourn times
        and Poisson-distributed adsorption events are assumed.  The parameter
        mapping is:

        - ``k_MT`` (molass) ≡ ``kd`` (Felinger desorption rate constant)
        - ``Nm`` (Felinger mass transfer units) = ``k_MT × k' × t0``
          where ``k' = R - 1`` (retention factor).

        This equivalence holds **only for linear isotherms** (b=0 in EDM).
        For nonlinear chromatography (fronting or tailing peaks), the LKM and
        SDM diverge.

    Skewness: a single LKM peak never fronts
        For **one component** the standardized third central moment of the LKM
        peak is, with ``N_d = Pe/2``, ``N_m = k_MT (R-1) t0`` and ``k' = R - 1``
        (Felinger *et al.* 2004, Eq. (39), equivalently Eq. (44)), ::

            S = 3 / sqrt(N_m N_d)
                * [N_m² (k'+1)³ + 2 N_m N_d k'² (k'+1) + 2 N_d² k'³]
                / [N_m (k'+1)² + 2 N_d k'²]^(3/2)

        Every quantity in it is positive, so **S > 0 for all physical
        parameters**: the peak is skewed to the tail and cannot front. The paper
        does not state this; it is deduced from the formula. (The formula is the
        standardized skew κ₃/κ₂^(3/2) of the characteristic function of its
        Eq. (52), which is the transfer function used here; ``lkm_pdf`` reproduces
        it numerically.) Limits: ``k' → 0`` (dispersion only): ``S = 3/sqrt(N_d)``;
        ``N_d → ∞`` (no axial dispersion, the Thomas model): ``S = 3/sqrt(2 N_m)``,
        which tends to 0 (a Gaussian) only as ``N_m → ∞``. ``k_MT → ∞`` gives the
        linear EDM, ``S = 3/sqrt(N_d)``; in between S is not monotonic in k_MT
        but stays positive.

        Scope of the statement:

        - one component (a sum of tailing components can look fronted where peaks
          overlap);
        - the **linear** isotherm, exponential sojourn times and Poisson
          adsorption events, which the paper names as the details that make the
          stochastic–dispersive model identical to this one;
        - the third standardized moment, not the asymmetry factor (it indicates
          tailing for a unimodal profile of this family; the mean against the
          peak position was not checked).

        Which models, for a single component (checked in
        ``tests/specific/300_SEC_Models/test_050_linear_models_skew.py``):

        - LKM, and the stochastic–dispersive model it is identical to: S > 0 from
          the formula above;
        - linear EDM (``EdmLinear.edm_pdf``, the ``k_MT → ∞`` limit): an inverse
          Gaussian, ``S = 3 sqrt(2/Pe) > 0`` exactly;
        - linear GRM (``GrmLinear.grm_pdf``): S > 0 on 400 000 random positive
          parameter sets (numerically, from the cumulants of its transfer function;
          not a proof). The paper's conclusion says the general rate and lumped
          pore models are equivalent to the LKM in linear chromatography, citing
          its ref. [38], which was not read here;
        - not covered: the lognormal-pore SDM, and any non-linear isotherm
          (the EDM with ``b < 0`` and the empirical EGH with ``tau < 0`` can front).

        So in linear chromatography fronting needs a non-linear isotherm
        (molass-library#350).

    Examples
    --------
    >>> import numpy as np
    >>> from molass.SEC.Models.LkmLinear import lkm_pdf
    >>> t = np.linspace(0.1, 20.0, 500)
    >>> y = lkm_pdf(t, Pe=500, t0=2.0, k_MT=1.667, R=4.0)
    >>> np.trapz(y, t)   # ≈ 1.0
    >>>
    >>> # With injection parameters:
    >>> y_phys = lkm_pdf(t, Pe=500, t0=2.0, k_MT=1.667, R=4.0, c_inj=0.5, t_inj=2.0)
    >>> np.trapz(y_phys, t)  # ≈ 1.0 (c_inj × t_inj = 0.5 × 2.0)
    """
    ts = 80.0 / (t0 * R) if timescale is None else timescale
    pdf_normalized = ts * _lkm_pdf_impl(ts * x, Pe, ts * t0, k_MT / ts, R)
    return c_inj * t_inj * pdf_normalized
