"""
SEC.Models.EdmLinear.py

PDF of the Equilibrium Dispersive Model (EDM) with a **linear isotherm**,
computed via characteristic function (CF) inversion using FFT.

This is the k_MT → ∞ limit of the LKM: when mass transfer is instantaneous
the stationary and mobile phases are always in local equilibrium, and the
only band-broadening mechanism is axial dispersion.

Assumptions
-----------
- Linear isotherm: q = a * c  (constant Henry coefficient; no overloading)
- Axial dispersion parametrised by the Peclet number Pe = u*L/D_ax
- Instantaneous mass transfer (equilibrium dispersive model)

Model parameters
----------------
Pe    : Peclet number  Pe = u*L/D_ax
t0    : dead time  t0 = L/u  (mobile-phase transit time)
R     : retention factor  R = t_R / t0 = 1 + F*a  (F = (1-ε)/ε, a = Henry coeff.)

Transfer function (Laplace domain)
------------------------------------
H(s) = exp( Pe/2 * (1 - sqrt(1 + 4*s*t0*R / Pe)) )

This is the k_MT → ∞ limit of the LKM transfer function:
  LKM:  Phi = (4*s*t0/Pe) * (s + k_MT*R) / (s + k_MT)
  EDM:  Phi = (4*s*t0*R / Pe)          [k_MT → ∞]

The elution profile is a perfect Gaussian with:
  μ₁ = t0 * R
  σ² = 2 * t0² * R² / Pe

This agrees with the classical moment formula (Qamar 2014, Table 1,
Dirichlet BCs, linear isotherm) and is validated in:
  molass-researcher/experiments/27_qamar_2014_paper/27b_edm_lkm_grm_consistency.ipynb

Note on edm_func (molass-legacy)
---------------------------------
``molass_legacy.SecTheory.Edm.edm_func`` implements the full EDM with a
quadratic isotherm (Langmuir linearisation, b ≠ 0) via the Hopf-Cole analytic
solution (Rehman 2022).  Its b=0 branch is mathematically equivalent to
``edm_pdf`` but uses a finite-column outlet-concentration formula that
introduces a small systematic mean shift (~0.5%) absent from this CF approach.

Use ``edm_pdf`` for:
  - Linear-regime SEC-SAXS analysis (analytical and comparative work)
  - Model-hierarchy checks: EDM < GRM < LKM

Use ``edm_func`` for:
  - Overloading / nonlinear isotherm studies (b ≠ 0)

References
----------
- Lapidus & Amundson (1952), J. Phys. Chem. 56:984
- Qamar et al. (2014), Comput. Chem. Eng. 71:383, Table 1
- Rehman et al. (2022), Thermal Science 26:4253 (nonlinear EDM)
- Validated in molass-researcher/experiments/27_qamar_2014_paper/27b
"""
import numpy as np
from molass.MathUtils.FftUtils import FftInvPdf


def edm_linear_cf(w, Pe, t0_s, R):
    """
    Characteristic function of the EDM elution profile (scaled coordinates).

    Parameters are in **scaled** time units (see ``edm_pdf`` for the scaling
    convention).  Do not call this directly; use ``edm_pdf`` instead.
    """
    s   = -1j * w
    Phi = (4.0 / Pe) * s * t0_s * R     # k_MT → ∞ limit of LKM Phi
    return np.exp(0.5 * Pe * (1.0 - np.sqrt(1.0 + Phi)))


_edm_pdf_impl = FftInvPdf(edm_linear_cf)


def edm_pdf(x, Pe, t0, R, timescale=None):
    """
    PDF of the EDM (Equilibrium Dispersive Model) elution profile with
    linear isotherm.

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
    R : float
        Retention factor  R = t_R / t0 = 1 + F*a
        (F = phase ratio = (1-ε)/ε, a = Henry coefficient).
    timescale : float or None, optional
        Time rescaling factor for the internal FFT grid.
        If ``None`` (default), chosen automatically as ``80 / (t0 * R)``,
        mapping the peak position t_R = t0*R to position 80 on the
        FFT grid ``[0, 1024]``.

    Returns
    -------
    ndarray
        Normalised PDF evaluated at each point in ``x``  (integral ≈ 1).
        Multiply by the peak area (c_inj × t_inj) to obtain absolute
        concentration units.

    Notes
    -----
    The profile is analytically a Gaussian with:
      μ₁ = t0 * R
      σ² = 2 * t0² * R² / Pe

    This is the narrowest of the three linear-isotherm SEC models:
      EDM  (this function) — axial dispersion only
      GRM  (GrmLinear.edm_pdf)  — axial + film/pore diffusion
      LKM  (LkmLinear.lkm_pdf)  — axial + lumped mass transfer

    The hierarchy EDM < GRM < LKM holds at all finite k_MT.

    Examples
    --------
    >>> import numpy as np
    >>> from molass.SEC.Models.EdmLinear import edm_pdf
    >>> t = np.linspace(0.1, 30.0, 500)
    >>> y = edm_pdf(t, Pe=400, t0=5.0, R=3.0)
    >>> np.trapz(y, t)   # ≈ 1.0
    """
    ts = 80.0 / (t0 * R) if timescale is None else timescale
    return ts * _edm_pdf_impl(ts * x, Pe, ts * t0, R)
