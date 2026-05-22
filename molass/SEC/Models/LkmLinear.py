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


def lkm_pdf(x, Pe, t0, k_MT, R, timescale=None):
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
    timescale : float or None, optional
        Time rescaling factor for the internal FFT grid.
        If ``None`` (default), chosen automatically as ``80 / (t0 * R)``,
        mapping the peak position t_R = t0*R to position 80 on the
        FFT grid ``[0, 1024]``.
        Override if the default produces edge artefacts (e.g. very wide peaks).

    Returns
    -------
    ndarray
        Normalised PDF evaluated at each point in ``x``  (integral ≈ 1).
        Multiply by the peak area (c_inj × t_inj) to obtain absolute
        concentration units.

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

    Examples
    --------
    >>> import numpy as np
    >>> from molass.SEC.Models.LkmLinear import lkm_pdf
    >>> t = np.linspace(0.1, 20.0, 500)
    >>> y = lkm_pdf(t, Pe=500, t0=2.0, k_MT=1.667, R=4.0)
    >>> np.trapz(y, t)   # ≈ 1.0
    """
    ts = 80.0 / (t0 * R) if timescale is None else timescale
    return ts * _lkm_pdf_impl(ts * x, Pe, ts * t0, k_MT / ts, R)
