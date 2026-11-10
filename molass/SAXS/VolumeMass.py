"""
    SAXS.VolumeMass.py

    Concentration-free mass of a particle from the volume of correlation Vc (Rambo and Tainer, Nature 496 (2013)
    477-481) of its scattering profile (molass-library#381).

    Vc = I(0) / integral(q I(q) dq)                          (A^2)
    Qr = Vc^2 / Rg
    M  = Qr / 0.1231                                         (Da, proteins; k = 1)

    The integral runs to the cut ``qmax_rg / Rg`` (Grant, J. Appl. Cryst. 55 (2022) 1116: 8 / Rg) and the part below
    the first measured q is taken from the Guinier law. No concentration and no Dmax are needed.

    Validity (molass-researcher experiment 57): the formula is a calibration on proteins. On the public data
    (aldolase, ovalbumin, glucose isomerase, BSA components) it is within about 10-17 % of the known mass; it agrees with
    the ATSAS program DATVC within about 10 %. Ideal homogeneous spheres come out about 40 % too light and a
    Gaussian chain depends strongly on its size, so the value says little about non-protein or strongly non-compact
    particles. Like the Porod volume it follows Rg along the elution for species of equal mass whose conformation
    changes, so a mass curve cannot tell a conformational continuum from species of different size.
"""
from dataclasses import dataclass, field

import numpy as np

RT_CONSTANT = 0.1231            # Rambo and Tainer (2013), proteins: M[Da] = Qr / 0.1231 (Qr in A^3)
DEFAULT_QMAX_RG = 8.0           # q cut in units of 1/Rg (Grant 2022)
MIN_POINTS = 20
NOTE = "protein calibration (Rambo and Tainer 2013); accuracy about 10-17 % on compact proteins, not for other particles"


@dataclass
class VolumeMass:
    """Result of :func:`volume_of_correlation`.

    Attributes
    ----------
    vc : float
        Volume of correlation (A^2); NaN if it could not be computed.
    qr : float
        ``Vc^2 / Rg`` (A^3).
    mass : float
        Mass in kDa (protein calibration); NaN if it could not be computed.
    rg, i0 : float
        The Rg (A) and I(0) used.
    q_cut : float
        The upper limit of the integral (1/A): ``qmax_rg / rg`` or the last q of the profile.
    n_points : int
        Number of measured points below the cut.
    reason : str or None
        Why the value is NaN, else None.
    """
    vc: float
    qr: float
    mass: float
    rg: float
    i0: float
    q_cut: float
    n_points: int
    reason: str = None
    note: str = field(default=NOTE, repr=False)

    def __bool__(self):
        return bool(np.isfinite(self.mass))


def volume_of_correlation(q, intensity, rg, i0, qmax_rg=DEFAULT_QMAX_RG, min_points=MIN_POINTS):
    """Vc, Qr and the mass (kDa) of a scattering profile.

    Parameters
    ----------
    q, intensity : array-like
        The profile (q in 1/A), in any intensity units (Vc does not depend on them).
    rg : float
        Radius of gyration (A), e.g. from the Guinier fit.
    i0 : float
        Forward scattering I(0) in the units of ``intensity``.
    qmax_rg : float, optional
        The integral runs up to ``qmax_rg / rg`` (default 8).
    min_points : int, optional
        Fewer measured points below the cut give NaN (default 20).

    Returns
    -------
    VolumeMass
        With ``mass`` in kDa. ``bool(result)`` is False when it could not be computed (see ``reason``).
    """
    q = np.asarray(q, dtype=float)
    intensity = np.asarray(intensity, dtype=float)
    if not (np.isfinite(rg) and rg > 0):
        return VolumeMass(np.nan, np.nan, np.nan, rg, i0, np.nan, 0, "no valid Rg")
    if not (np.isfinite(i0) and i0 > 0):
        return VolumeMass(np.nan, np.nan, np.nan, rg, i0, np.nan, 0, "no positive I(0)")
    q_cut = qmax_rg/rg
    m = np.isfinite(q) & np.isfinite(intensity) & (q <= q_cut)
    n = int(m.sum())
    if n < min_points:
        return VolumeMass(np.nan, np.nan, np.nan, rg, i0, q_cut, n,
                          f"only {n} points below q = {q_cut:.3g} (8/Rg), at least {min_points} needed")
    qq, ii = q[m], intensity[m]
    area = np.trapezoid(qq*ii, qq)
    area += i0*3/(2*rg**2)*(1 - np.exp(-qq[0]**2*rg**2/3))     # 0 .. q_1 with the Guinier law
    if not area > 0:
        return VolumeMass(np.nan, np.nan, np.nan, rg, i0, q_cut, n, "the integral of q I(q) is not positive")
    vc = i0/area
    qr = vc**2/rg
    return VolumeMass(float(vc), float(qr), float(qr/RT_CONSTANT/1000.0), float(rg), float(i0), float(q_cut), n)


@dataclass
class VolumeMassCurve:
    """Per-frame Rg, I(0), Vc and mass (kDa) along the elution (:meth:`SecSaxsData.get_volume_mass_curve`).
    Frames without a reliable Guinier fit or with too few points carry NaN."""
    frames: np.ndarray
    rg: np.ndarray
    i0: np.ndarray
    vc: np.ndarray
    mass: np.ndarray
    note: str = NOTE

    def plot(self, ax=None, **kwargs):
        """Mass (kDa, left axis) and Rg (A, right axis) against the frame number."""
        import matplotlib.pyplot as plt
        if ax is None:
            _, ax = plt.subplots()
        ax.plot(self.frames, self.mass, "o-", ms=3, color="C1", **kwargs)
        ax.set_xlabel("frame")
        ax.set_ylabel("volume-of-correlation mass (kDa)", color="C1")
        ax2 = ax.twinx()
        ax2.plot(self.frames, self.rg, "s-", ms=2, color="C0", alpha=0.6)
        ax2.set_ylabel("Rg (A)", color="C0")
        return ax


def volume_mass_curve(xr, rgcurve, score_min=0.6, intensity_frac=0.2, qmax_rg=DEFAULT_QMAX_RG):
    """The :class:`VolumeMassCurve` of the XR data ``xr`` from the per-frame Guinier fits of ``rgcurve``.

    Frames are used when their Guinier score is at least ``score_min`` and their I(0) is at least
    ``intensity_frac`` of the maximum I(0) (the mass of a frame at the wings of the peak is noise).
    The integral uses the intensity of the frame itself (its column of ``xr.M``)."""
    frames = np.asarray(rgcurve.frames)
    rgs = np.asarray(rgcurve.rgs, dtype=float)
    i0s = np.asarray(rgcurve.i0s, dtype=float)
    scores = np.asarray(rgcurve.scores, dtype=float)
    ok = np.isfinite(rgs) & (rgs > 0) & (rgs < 99) & np.isfinite(i0s) & (i0s > 0) & np.isfinite(scores) & (scores >= score_min)
    if ok.any():
        ok &= i0s >= intensity_frac*np.max(i0s[ok])
    jv = np.asarray(xr.jv)
    vc = np.full(len(frames), np.nan)
    mass = np.full(len(frames), np.nan)
    for k in np.where(ok)[0]:
        col = int(np.searchsorted(jv, frames[k]))
        r = volume_of_correlation(xr.qv, xr.M[:, col], rgs[k], i0s[k], qmax_rg=qmax_rg)
        vc[k], mass[k] = r.vc, r.mass
    keep = ok & np.isfinite(mass)
    return VolumeMassCurve(frames[keep], rgs[keep], i0s[keep], vc[keep], mass[keep])
