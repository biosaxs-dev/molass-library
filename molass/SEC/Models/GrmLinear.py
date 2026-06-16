"""
SEC.Models.GrmLinear.py

PDF of the General Rate Model (GRM) with a **linear isotherm**, computed via
characteristic function (CF) inversion using FFT (PDE-based).

The GRM is the most physically detailed of the three linear-isotherm SEC
transport models available in this package:

  EDM (EdmLinear) — axial dispersion only (k_MT → ∞ limit)
  LKM (LkmLinear) — axial dispersion + lumped mass transfer
  GRM (this file)  — axial dispersion + film mass transfer + pore diffusion

Assumptions
-----------
- Linear isotherm: q = a_star * c  inside the pore  (no overloading)
- Axial dispersion parametrised by the Peclet number Pe = u*L/D_ax
- External (film) mass transfer with rate constant k_ext [length/time]
- Intraparticle pore diffusion with effective diffusivity D_eff [length²/time]
- Spherical particles of radius R_p
- Intraparticle porosity eps_p absorbed into a_star:
    a_star = eps_p + (1 - eps_p) * a_henry
  where a_henry is the Henry coefficient for adsorption on the pore wall.
  For non-porous particles set eps_p = 0; then a_star = a_henry.

Model parameters
----------------
Pe      : Peclet number  Pe = u*L/D_ax
t0      : dead time  t0 = L/u  (mobile-phase transit time)
k_ext   : external film mass-transfer coefficient [length/time]
R_p     : particle radius [length]
D_eff   : effective intraparticle pore diffusivity [length²/time]
          Large D_eff (film-only limit) → k_MT_eff = 3*F*k_ext / (R_p * R)
a_star  : effective intraparticle retention parameter (see Assumptions above)
F_ratio : phase ratio  F = (1 - ε) / ε  (ε = interstitial porosity)

Retention factor
----------------
R_eff = 1 + F_ratio * a_star

Transfer function (Laplace domain, Qamar 2014 eqs. 22–24, 37)
---------------------------------------------------------------
φ(s) = s + (3*F*k_ext/R_p) * (1 − f(s))

f(s) = B_p / (B_p − 1 + ξ·coth(ξ))
     where  ξ = sqrt(a_star * s / D_eff) * R_p
            B_p = k_ext * R_p / D_eff

H(s) = exp( Pe/2 * (1 − sqrt(1 + 4*t0*φ(s)/Pe)) )

Moment formulas (Qamar 2014 Table 1, Dirichlet BCs, linear isotherm)
----------------------------------------------------------------------
μ₁     = t0 * R_eff
σ²_GRM = 2*t0²*R_eff²/Pe  +  2*t0*(R_eff−1)²/(R_eff * k_MT_eff)

where k_MT_eff = 3*F*k_ext / (R_p * R_eff)   [film-only limit, large D_eff]

GRM ↔ LKM moment matching (Qamar 2014, Appendix C)
----------------------------------------------------
Given GRM k_MT_eff and R, the equivalent LKM k_MT is:
  k_MT_LKM = R / (R−1) * k_MT_eff

LKM initialisation from GRM result:
  k_ext = k_MT_LKM * (R−1)/R * R_p / (3*F/R)
        = k_MT_LKM * (R−1) * R_p / (3*F)

References
----------
- Qamar et al. (2014), Comput. Chem. Eng. 71:383–399 (GRM CF formula)
- Validated in molass-researcher/experiments/27_qamar_2014_paper/27a, 27b
  - μ₁ error: 0.00%,  σ² error: 0.00% vs Qamar 2014 Table 1
  - Timing: ~1.1× LKM overhead
"""
import numpy as np
from molass.MathUtils.FftUtils import FftInvPdf


def grm_linear_cf(w, Pe, t0_s, k_ext_s, R_p, D_eff_s, a_star, F_ratio):
    """
    Characteristic function of the GRM elution profile (scaled coordinates).

    Parameters are in **scaled** time units (see ``grm_pdf`` for the scaling
    convention).  Do not call this directly; use ``grm_pdf`` instead.
    """
    s         = -1j * w
    alpha     = a_star * s / D_eff_s
    xi        = np.sqrt(alpha + 0j) * R_p
    coth_xi   = np.where(np.abs(xi) < 1e-8,
                         1.0 / (xi + 1e-300),
                         np.cosh(xi) / np.sinh(xi))
    B_p       = k_ext_s * R_p / D_eff_s
    f_s       = B_p / (B_p - 1.0 + xi * coth_xi)
    phi       = s + (3.0 * F_ratio * k_ext_s / R_p) * (1.0 - f_s)
    Phi       = (4.0 / Pe) * t0_s * phi
    return np.exp(0.5 * Pe * (1.0 - np.sqrt(1.0 + Phi)))


_grm_pdf_impl = FftInvPdf(grm_linear_cf)


def grm_pdf(x, Pe, t0, k_ext, R_p, D_eff, a_star, F_ratio, timescale=None):
    """
    PDF of the GRM (General Rate Model) elution profile with linear isotherm.

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
    k_ext : float
        External film mass-transfer coefficient [length/time].
        Must use the same length unit as ``R_p``.
    R_p : float
        Particle radius [length].
    D_eff : float
        Effective intraparticle pore diffusivity [length²/time].
        Use a large value (e.g. 1e3 cm²/min) to approximate the film-only
        (no pore diffusion resistance) limit where:
          k_MT_eff = 3 * F_ratio * k_ext / (R_p * R_eff)
    a_star : float
        Effective intraparticle retention parameter.
        a_star = eps_p + (1 - eps_p) * a_henry
        where eps_p is the intraparticle porosity and a_henry is the Henry
        coefficient.  For non-porous particles (eps_p=0): a_star = a_henry.
    F_ratio : float
        Phase ratio  F = (1 - ε) / ε  (ε = interstitial/column porosity).
    timescale : float or None, optional
        Time rescaling factor for the internal FFT grid.
        If ``None`` (default), chosen automatically as
        ``80 / (t0 * max(1, R_eff))`` where ``R_eff = 1 + F_ratio * a_star``.

    Returns
    -------
    ndarray
        Normalised PDF evaluated at each point in ``x``  (integral ≈ 1).
        Multiply by the peak area (c_inj × t_inj) to obtain absolute
        concentration units.

    Notes
    -----
    Model hierarchy (linear isotherm)
        EDM  (EdmLinear.edm_pdf)  — narrowest, axial dispersion only
        GRM  (this function)       — intermediate width
        LKM  (LkmLinear.lkm_pdf)  — broadest, lumped mass transfer

    LKM initialisation
        Given a GRM result (k_ext, R_p, R), the equivalent LKM k_MT is:
          k_MT_LKM = R / (R−1) × k_MT_eff
        where k_MT_eff = 3 * F * k_ext / (R_p * R).
        Inverse: k_ext = k_MT_LKM * (R−1) * R_p / (3 * F)

    Units
        All length parameters (k_ext, R_p, D_eff) must use consistent units.
        Typical choices: [cm] and [min] (k_ext in cm/min, D_eff in cm²/min).

    Examples
    --------
    >>> import numpy as np
    >>> from molass.SEC.Models.GrmLinear import grm_pdf
    >>> t   = np.linspace(1.0, 50.0, 3000)
    >>> eps = 0.4; F = (1 - eps) / eps  # = 1.5
    >>> R   = 3.0; a = (R - 1) / F      # Henry coeff
    >>> y = grm_pdf(t, Pe=400, t0=5.0, k_ext=0.00533, R_p=0.004,
    ...             D_eff=1e3, a_star=a, F_ratio=F)
    >>> np.trapz(y, t)   # ≈ 1.0
    """
    if timescale is None:
        R_eff = 1.0 + F_ratio * a_star
        ts = 80.0 / (t0 * max(1.0, R_eff))
    else:
        ts = timescale
    return ts * _grm_pdf_impl(
        ts * x, Pe, ts * t0,
        k_ext / ts, R_p, D_eff / ts,
        a_star, F_ratio
    )
