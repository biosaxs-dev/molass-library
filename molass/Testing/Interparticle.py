"""
    Testing.Interparticle.py

    Frames with a known interparticle term, ``M(q, t) = A(q) c(t) + B(q) c(t)^2``, for testing how methods behave when the
    interparticle effect is present (molass-library#415; molass-researcher experiments 64 and 65, where these helpers were
    first written and used).

    Decoupling approximation: ``I(q) = P(q) S(q)`` with an isotropic effective hard-sphere ``S(q)``, so to first order in the
    concentration

        B(q) = -K Phi(2 q R_eff) A(q),     A(q) = I0 P(q)   (P(0) = 1),

    where ``R_eff`` is the radius of the hard sphere with the same orientation-averaged excluded volume as the particle
    (``V_ex = 2 V + S * mean width`` for a convex body, ``32 pi R^3 / 3`` for a sphere) and ``K`` the strength for a
    concentration curve with peak 1. ``Phi`` is :func:`molass.SAXS.Theory.SolidSphere.phi`.

    Typical use::

        qv = np.linspace(0.01, 0.3, 300)
        A = 0.33 * sphere_form_factor(qv, 33.0)
        B = hard_sphere_B(qv, A, K=0.255, R_eff=np.sqrt(5/3) * 33.0)
        fr = interparticle_frames(A, B, c, qv, error=0.002, noise_scale=1.0, seed=0)
        fr.M, fr.E                 # the data and the stated error
        fr.truth_on(trimmed_qv)    # (A, B) on any q grid, to score a method on the grid it was run on

    Notes
    -----
    * ``noise_scale`` multiplies the stated error: 1 is the stated level. (On the real SAMPLE3 the stated error is on the right
      scale: ``ssd.xr.error_scale()``, #416; the first experiments used 2.5 by mistake.)
    * The automatic trimming of ``trimmed_copy()`` depends on the noise and on the interaction (the first q kept was 0.0075,
      0.018 or 0.034 for the same truth), so a truth on the generating grid cannot be compared point by point with a result on
      the trimmed grid: use ``truth_on``. Score with a fixed window.
    * :meth:`InterparticleFrames.to_ssd` builds a ``SecSaxsData``; ``compute_scds()`` needs a ``beamline_info`` (assign
      ``ssd.beamline_info`` from a real data set, otherwise it raises "concfactor is not given").
"""
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

from molass.SAXS.Theory.SolidSphere import phi


def sphere_form_factor(qv, rg):
    """P(q) of a homogeneous sphere with the radius of gyration ``rg`` (R = sqrt(5/3) rg), P(0) = 1."""
    return phi(np.asarray(qv, dtype=float), np.sqrt(5 / 3) * rg) ** 2


def debye_form_factor(qv, rg):
    """P(q) of a Gaussian chain (Debye function) with the radius of gyration ``rg``, P(0) = 1."""
    x = (np.asarray(qv, dtype=float) * rg) ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(x < 1e-6, 1 - x / 3, 2 * (np.exp(-x) - 1 + x) / x ** 2)


def _fibonacci_sphere(n):
    i = np.arange(n) + 0.5
    z = 1 - 2 * i / n
    t = np.pi * (1 + 5 ** 0.5) * i
    r = np.sqrt(1 - z ** 2)
    return np.column_stack([r * np.cos(t), r * np.sin(t), z])


def scale_axes_to_rg(axes, rg):
    """Semi-axes ``axes`` of a homogeneous tri-axial ellipsoid scaled so that ``Rg = sqrt((a^2 + b^2 + c^2) / 5)`` equals ``rg``."""
    axes = np.asarray(axes, dtype=float)
    return axes * rg / np.sqrt(np.sum(axes ** 2) / 5)


def ellipsoid_form_factor(qv, axes, n_orient=3000):
    """Orientation-averaged P(q) of a homogeneous tri-axial ellipsoid with semi-axes ``axes`` (P(0) = 1)."""
    a, b, c = axes
    q = np.asarray(qv, dtype=float)
    d = _fibonacci_sphere(n_orient)
    s = np.sqrt((a * d[:, 0]) ** 2 + (b * d[:, 1]) ** 2 + (c * d[:, 2]) ** 2)      # radius along each direction
    u = q[:, None] * s[None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        f = np.where(u < 1e-3, 1 - u ** 2 / 10, 3 * (np.sin(u) - u * np.cos(u)) / u ** 3)
    return np.mean(f ** 2, axis=1)


def ellipsoid_excluded_volume(axes, n=400):
    """Orientation-averaged excluded volume of two identical convex bodies, ``V_ex = 2 V + S * (mean width)``, for a tri-axial ellipsoid."""
    a, b, c = axes
    V = 4 / 3 * np.pi * a * b * c
    x, w = np.polynomial.legendre.leggauss(n)                       # cos(theta)
    ph = np.linspace(0, 2 * np.pi, 2 * n, endpoint=False)
    X, P = np.meshgrid(x, ph, indexing="ij")
    st = np.sqrt(1 - X ** 2)
    dS = np.sqrt((b * c * st * np.cos(P)) ** 2 + (a * c * st * np.sin(P)) ** 2 + (a * b * X) ** 2)
    S = np.sum(w[:, None] * dS) * (2 * np.pi / (2 * n))
    d = _fibonacci_sphere(20000)
    mean_width = 2 * np.mean(np.sqrt((a * d[:, 0]) ** 2 + (b * d[:, 1]) ** 2 + (c * d[:, 2]) ** 2))
    return 2 * V + S * mean_width


def effective_radius(axes):
    """Radius of the hard sphere with the same excluded volume as a tri-axial ellipsoid with semi-axes ``axes`` (``V_ex = 32 pi R^3 / 3``)."""
    return (3 * ellipsoid_excluded_volume(axes) / (32 * np.pi)) ** (1 / 3)


def hard_sphere_B(qv, A, K, R_eff):
    """``B(q) = -K Phi(2 q R_eff) A(q)``: the c^2 term of the decoupling approximation (``K`` for a concentration curve with peak 1)."""
    return -K * phi(np.asarray(qv, dtype=float), 2 * R_eff) * np.asarray(A, dtype=float)


def _as_function(values, qv, name):
    if callable(values):
        return values
    values = np.asarray(values, dtype=float)
    if values.shape != np.shape(qv):
        raise ValueError(f"{name} must be a function of q or an array with one value per q point")
    grid = np.asarray(qv, dtype=float)
    return lambda q: np.interp(np.asarray(q, dtype=float), grid, values)


@dataclass
class InterparticleFrames:
    """Simulated frames ``M = A c^T + B (c^2)^T + noise`` with their truth.

    Attributes
    ----------
    M, E : numpy.ndarray, shape (n_q, n_frames)
        The data and the stated error (``M`` has noise ``noise_scale * E``).
    qv, jv : numpy.ndarray
    c : numpy.ndarray
        The concentration curve as given (use peak 1 for ``K`` to mean what ``hard_sphere_B`` says).
    A, B : numpy.ndarray
        The true profiles on ``qv``.
    noise_scale : float
    seed : int
    K, R_eff : float or None
        The true strength and effective radius, if given.
    """
    M: np.ndarray
    E: np.ndarray
    qv: np.ndarray
    jv: np.ndarray
    c: np.ndarray
    A: np.ndarray
    B: np.ndarray
    noise_scale: float
    seed: int
    K: float = None
    R_eff: float = None
    _A_of_q: object = None
    _B_of_q: object = None

    def truth_on(self, qv):
        """``(A, B)`` on the q grid ``qv``: evaluated if ``A`` and ``B`` were given as functions of q, linearly interpolated otherwise."""
        return self._A_of_q(qv), self._B_of_q(qv)

    def to_ssd(self, wv=None, uv_frames=None, slope=None, intercept=None, uv_noise=None, trimmed=False):
        """A ``SecSaxsData`` of these frames with a UV matrix proportional to the true concentration, so that the whole chain
        (``trimmed_copy().corrected_copy().quick_decomposition(1)``) can be run.

        The UV intensity at the XR frame ``f`` is ``UV_SCALE * spectrum(wavelength) * c(f)`` with the protein spectrum of
        :class:`molass.Testing.Simulator.Species`; the UV frame of the XR frame ``f`` is ``slope * f + intercept`` (default: the
        nominal mapping of SAMPLE1, ``1.4493`` and ``3.464``). The true mapping is stored in ``ssd.simulation_truth.mapping``.
        """
        from molass.DataObjects import SecSaxsData as SSD
        from molass.Testing import Simulator as sim
        wv = sim.WV if wv is None else np.asarray(wv, dtype=float)
        slope = sim.SLOPE if slope is None else slope
        intercept = sim.INTERCEPT if intercept is None else intercept
        if uv_frames is None:
            uv_frames = np.arange(int(np.floor(intercept)), int(np.ceil(slope * self.jv[-1] + intercept)) + 2)
        uv_frames = np.asarray(uv_frames)
        f_xr = (uv_frames - intercept) / slope
        c_uv = np.interp(f_xr, self.jv, self.c, left=0.0, right=0.0)
        spectrum = sim.Species(amp=1.0, center=0.0, sigma=1.0, mass=1.0, rg=30.0).spectrum(wv)
        rng = np.random.default_rng(self.seed + 1)
        sigma_uv = sim.SIGMA_UV if uv_noise is None else uv_noise
        A_uv = sim.UV_SCALE * spectrum[:, None] * c_uv[None, :] + self.noise_scale * sigma_uv * rng.standard_normal((len(wv), len(uv_frames)))
        ssd = SSD.from_arrays(self.M, self.qv, self.E, xr_jv=self.jv, uv_M=A_uv, uv_wv=wv, uv_jv=uv_frames, trimmed=trimmed)
        ssd.simulation_truth = SimpleNamespace(frames=self, mapping=(slope, intercept))
        return ssd


def interparticle_frames(A, B, c, qv, error, noise_scale=1.0, seed=0, jv=None, K=None, R_eff=None):
    """Frames ``M(q, t) = A(q) c(t) + B(q) c(t)^2 + noise`` with the truth attached (molass-library#415).

    Parameters
    ----------
    A, B : array-like (one value per q point) or callable ``f(q)``
        The true scattering profile of the species and of the interparticle term. Callables allow ``truth_on`` to be exact on any grid.
    c : array-like, shape (n_frames,)
        The concentration curve (peak 1 is the convention of ``K``).
    qv : array-like
    error : float, array of shape (n_q,) or array of shape (n_q, n_frames)
        The stated error. It is also the unit of the noise: ``noise = noise_scale * error * N(0, 1)``.
    noise_scale : float, optional
        1 is the stated level; 0 gives noise-free frames.
    seed : int, optional
    jv : array-like, optional
        Frame indices (default ``0 ... n_frames - 1``).
    K, R_eff : float, optional
        Stored in the result when the truth was generated with :func:`hard_sphere_B`.

    Returns
    -------
    InterparticleFrames
    """
    qv = np.asarray(qv, dtype=float)
    c = np.asarray(c, dtype=float)
    jv = np.arange(len(c)) if jv is None else np.asarray(jv)
    if len(jv) != len(c):
        raise ValueError("jv and c must have the same length")
    fa, fb = _as_function(A, qv, "A"), _as_function(B, qv, "B")
    a, b = np.asarray(fa(qv), dtype=float), np.asarray(fb(qv), dtype=float)
    E = np.broadcast_to(np.asarray(error, dtype=float).reshape(-1, 1) if np.ndim(error) == 1 else np.asarray(error, dtype=float),
                        (len(qv), len(c))).copy()
    rng = np.random.default_rng(seed)
    M = a[:, None] * c[None, :] + b[:, None] * (c ** 2)[None, :] + noise_scale * E * rng.standard_normal(E.shape)
    return InterparticleFrames(M=M, E=E, qv=qv, jv=jv, c=c, A=a, B=b, noise_scale=float(noise_scale), seed=int(seed), K=K, R_eff=R_eff,
                               _A_of_q=fa, _B_of_q=fb)
