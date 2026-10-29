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
        - the **linear** isotherm. The equivalence of the stochastic–dispersive model
          (SDM) with this one needs, in Felinger's words, "exponential distribution for
          the sojourn times and Poisson distribution for the number of adsorption
          events" (homogeneous kinetics): without these details the two are not
          equivalent. Heterogeneous kinetics (e.g. a pore-size distribution) is the
          SDM's extension beyond the LKM (replace φ_S by the CF of the heterogeneous
          kinetics, his conclusions), so "SDM = LKM in general" is **not** what the
          paper establishes; the positivity below does not need it;
        - the third standardized moment, not the asymmetry factor (it indicates
          tailing for a unimodal profile of this family; the mean against the
          peak position was not checked).

        Which models, for a single component (checked in
        ``tests/specific/300_SEC_Models/test_050_linear_models_skew.py``):

        - LKM: S > 0 from the formula above;
        - the SDM with **any** positive sojourn-time law (exponential, gamma, a
          pore-size mixture): in Felinger's Eq. (32) the cumulants are, with
          ``Y₁ = n E[τ] + t0`` and ``Y_k = n E[τ^k]`` (k ≥ 2),
          ``κ₂ = Y₂ + Y₁²/N_d`` and ``κ₃ = Y₃ + 3 Y₁ Y₂/N_d + 3 Y₁³/N_d²``, all terms
          positive, so S > 0 (it gives Eq. (44) for exponential sojourn times; the
          chain rule is the whole proof);
        - molass's SDM (``SdmMonoPore``, its gamma form, ``LognormalPore``) uses the
          second-order form ``exp(Z + Z²/(2 N0))`` instead of Felinger's exact
          first-passage form ``exp[N_d (1 − sqrt(1 − 2Z/N_d))]``: the same mean and
          variance (``N0`` plays the role of ``N_d``) but ``κ₃ = Y₃ + 3 Y₁ Y₂/N0``,
          positive for any adsorption (``n > 0``) and zero without it, since the
          mobile-phase dispersion is then Gaussian. Its skew equals this expression
          exactly (checked on ``sdm_monopore_pdf``) and is below the LKM's when ``N0``
          is small (0.156 against 0.443 at ``N0 = 40``, n = 60, τ = 0.2, t0 = 10), the
          same at ``N0 = 14400``. So molass's SDM is not the LKM exactly either. The
          lognormal-pore form is the pore-size mixture of Sepsey, Bacskay and Felinger
          (2014, J. Chromatogr. A 1331:52), Eq. (18)-(21), plus molass's own mobile-phase
          dispersion term (the paper neglects axial dispersion): its cumulants
          ``Y_k = ∫ f(r) N K_e(r) k! (T K_p(r))^k dr`` are the paper's Eq. (22)-(25)
          (third central moment ``6 n_perm τ_perm³ a``, ``a`` an integral of a positive
          function), reproduced to 8 digits for integer exponents ``η = m_e + k m_p`` of
          both signs of ``m_p``, so they are positive; in the paper every plotted skew is
          positive (Fig. 3-5). molass integrates up to ``min(600, mode + 5 stdev)``
          instead of infinity, which drops 0.3-2.6 % of the pore mass for σ = 0.3-1.5.
          The mixture was tested through its moments, the dispersion form only on the
          mono-pore ``sdm_monopore_pdf``;
        - linear EDM (``EdmLinear.edm_pdf``, the ``k_MT → ∞`` limit): an inverse
          Gaussian, ``S = 3 sqrt(2/Pe) > 0`` exactly;
        - linear GRM (``GrmLinear.grm_pdf``): S > 0 from Qamar *et al.* (2014,
          Chem. Eng. Sci. 107:192), Table 1 (Dirichlet boundary conditions): the third
          central moment is a sum of three positive terms. The transfer function used
          here reproduces the table's mean, variance and third moment to rounding
          error, and S > 0 also holds on 400 000 random positive parameter sets. The
          GRM is **not identical** to the LKM, though: in the paper's Table 3 / Fig. 12
          no single LKM rate constant matches both the second and the third moment of
          the GRM (differences of about 4 % and 14 % at best), so Felinger's remark
          that the general rate model is equivalent to the LKM in linear
          chromatography (his ref. [38], not read here) cannot be read as identity;
        - not covered: any non-linear isotherm
          (the EDM with ``b < 0`` and the empirical EGH with ``tau < 0`` can front).

        (Qamar's "front asymmetry" is the third moment, not fronting: his positive
        skewness ``β = μ₃'/(μ₂')^(3/2)`` means a right-skewed, i.e. tailed, peak.)

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
