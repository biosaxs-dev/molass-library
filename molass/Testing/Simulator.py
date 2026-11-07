"""
    Testing.Simulator.py

    A known-truth SEC-SAXS simulator (molass-library#340): species with Gaussian elution,
    sphere-like scattering and UV spectra, and a UV->XR mapping, to verify analyses against
    the truth (mapping resolution, homogeneity, decompositions, ...).

    Model (SAMPLE1 geometry by default): ``I(q, f) = sum_i m_i c_i(f) P_i(q)`` (``P_i`` is the sphere form
    factor unless ``Species.shape`` says otherwise) and
    ``A(lambda, u) = sum_i s c_i(f_u) eps_i(lambda)`` where ``c_i`` is the Gaussian elution of
    species i and the UV frame u sees the XR frame ``f_u = (u - intercept) / slope - uv_late``.
"""
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

QV = np.linspace(0.0143, 0.4268, 984)
WV = np.linspace(250.112, 449.959, 254)
XR_FRAMES = np.arange(241)
UV_FRAMES = np.arange(3, 352)
SLOPE, INTERCEPT = 1.4493, 3.464    # the UV->XR mapping of SAMPLE1
SIGMA_XR, SIGMA_UV, UV_SCALE = 0.02, 0.0007, 0.5


def sphere(q, rg):
    """Scattering profile of a homogeneous sphere with the radius of gyration ``rg``."""
    x = q * rg * np.sqrt(5 / 3)
    return (3 * (np.sin(x) - x * np.cos(x)) / x ** 3) ** 2


def protein(w):
    return np.exp(-0.5 * ((w - 278) / np.where(w < 278, 17.0, 12.0)) ** 2)


def nucleic(w):
    return np.exp(-0.5 * ((w - 260) / 20.0) ** 2)


def scatter(w):
    return (w / 320.0) ** -4


SHAPE_NAMES = ("sphere", "ellipsoid", "cylinder", "chain")
DEFAULT_SHAPE_ARG = {"ellipsoid": 3.0, "cylinder": 10.0}
_COARSE_Q_POINTS = 250      # form factors of non-spherical shapes are evaluated on this grid and interpolated


def shape_profile(shape, rg, qv, shape_arg=None):
    """Normalized scattering profile ``P(q)`` (``P(0) = 1``) of a particle with radius of gyration ``rg``.

    Parameters
    ----------
    shape : str or callable
        ``"sphere"``, ``"ellipsoid"`` (prolate of revolution, semi-axes R, R, eps*R; ``shape_arg`` = eps,
        default 3), ``"cylinder"`` (``shape_arg`` = length/radius, default 10), ``"chain"`` (Gaussian
        chain), or a callable ``f(q, rg)`` returning ``P(q)``. The shapes are the exact form factors of
        :mod:`molass.Kratky.FormFactors`, scaled so that their Rg is ``rg``.
    rg : float
    qv : array-like
    shape_arg : float, optional
    """
    qv = np.asarray(qv, dtype=float)
    if callable(shape):
        return np.asarray(shape(qv, rg), dtype=float)
    if shape == "sphere":
        return sphere(qv, rg)
    from molass.Kratky import FormFactors as ff
    if shape == "ellipsoid":
        eps = DEFAULT_SHAPE_ARG["ellipsoid"] if shape_arg is None else shape_arg
        fn = lambda q: ff.ellipsoid_P(q, rg/ff.ellipsoid_Rg(1.0, eps), eps)
    elif shape == "cylinder":
        aspect = DEFAULT_SHAPE_ARG["cylinder"] if shape_arg is None else shape_arg
        R = rg/ff.cylinder_Rg(1.0, aspect)
        fn = lambda q: ff.cylinder_P(q, R, aspect*R)
    elif shape in ("chain", "gaussian_chain"):
        fn = lambda q: ff.gaussian_chain_P(q, rg)
    else:
        raise ValueError(f"unknown shape {shape!r}; use one of {SHAPE_NAMES} or a callable f(q, rg)")
    if len(qv) <= _COARSE_Q_POINTS:
        return fn(qv)
    from scipy.interpolate import CubicSpline
    coarse = np.linspace(qv.min(), qv.max(), _COARSE_Q_POINTS)
    return CubicSpline(coarse, fn(coarse))(qv)


@dataclass
class Species:
    """One species: Gaussian elution (``amp``, ``center`` and ``sigma`` in XR frames), scattering mass
    ``mass`` and radius of gyration ``rg``, UV extinction at 280 nm ``eps280``, nucleic-acid
    contribution ``na`` and turbidity ``turb`` of the UV spectrum.

    ``shape`` (default ``"sphere"``) is the form factor, see :func:`shape_profile`: ``"ellipsoid"``,
    ``"cylinder"``, ``"chain"`` or a callable ``f(q, rg)``; ``shape_arg`` is its extra parameter
    (ellipsoid axial ratio, cylinder length/radius). ``rg`` sets the scale in every case."""
    amp: float
    center: float
    sigma: float
    mass: float
    rg: float
    eps280: float = 1.0
    na: float = 0.0
    turb: float = 0.01
    shape: object = "sphere"
    shape_arg: float = None

    def spectrum(self, wv=WV):
        return self.eps280 * (protein(wv) / protein(280.0) + self.na * nucleic(wv) + self.turb * scatter(wv))

    def elution(self, f):
        return self.amp * np.exp(-0.5 * ((f - self.center) / self.sigma) ** 2)


def clean_signals(species, uv_late=0.0, slope=SLOPE, intercept=INTERCEPT,
                  qv=QV, wv=WV, xr_frames=XR_FRAMES, uv_frames=UV_FRAMES):
    """The noise-free XR matrix ``I(q, frame)`` and UV matrix ``A(wavelength, frame)``."""
    I = np.zeros((len(qv), len(xr_frames)))
    A = np.zeros((len(wv), len(uv_frames)))
    f_uv = (uv_frames - intercept) / slope - uv_late        # the XR frame whose material is at each UV frame
    for s in species:
        I += (s.mass * s.elution(xr_frames))[None, :] * shape_profile(s.shape, s.rg, qv, s.shape_arg)[:, None]
        A += UV_SCALE * s.spectrum(wv)[:, None] * s.elution(f_uv)[None, :]
    return I, A


def simulate_ssd(species, uv_late=0.0, noise=1.0, seed=0, slope=SLOPE, intercept=INTERCEPT,
                 qv=QV, wv=WV, xr_frames=XR_FRAMES, uv_frames=UV_FRAMES):
    """A SecSaxsData of simulated data with known truth, built with ``SecSaxsData.from_arrays``.

    Parameters
    ----------
    species : list of Species
        The species.
    uv_late : float, optional
        The UV trace is this many XR frames later than the nominal mapping says (a mapping
        error to be recovered); default 0 (the nominal mapping is exact).
    noise : float, optional
        Scale of the Gaussian noise (1 is the level of SAMPLE1); 0 gives noise-free data.
    seed : int, optional
        Seed of the noise.
    slope, intercept : float, optional
        The nominal UV->XR mapping ``uv_frame = slope * xr_frame + intercept``.
    qv, wv, xr_frames, uv_frames : array-like, optional
        The axes; default is the SAMPLE1 geometry (984 q-values, 254 wavelengths,
        XR frames 0-240, UV frames 3-351).

    Returns
    -------
    ssd : SecSaxsData
        Marked as trimmed and corrected (the simulation has no baseline). The truth is attached
        as ``ssd.simulation_truth`` with ``species``, ``uv_late``, ``mapping`` (the nominal
        ``(slope, intercept)``) and ``true_mapping`` (``(slope, intercept)`` of the mapping that
        matches the data, i.e. the nominal one shifted by ``uv_late`` XR frames).
    """
    from molass.DataObjects import SecSaxsData as SSD
    I, A = clean_signals(species, uv_late, slope, intercept, qv, wv, xr_frames, uv_frames)
    rng = np.random.default_rng(seed)
    I = I + noise * SIGMA_XR * rng.standard_normal(I.shape)
    A = A + noise * SIGMA_UV * rng.standard_normal(A.shape)
    E = np.full_like(I, max(noise, 1e-3) * SIGMA_XR)
    ssd = SSD.from_arrays(I, np.asarray(qv), E, xr_jv=np.asarray(xr_frames),
                          uv_M=A, uv_wv=np.asarray(wv), uv_jv=np.asarray(uv_frames), trimmed=True)
    ssd.simulation_truth = SimpleNamespace(
        species=list(species), uv_late=uv_late, mapping=(slope, intercept),
        true_mapping=(slope, intercept + slope * uv_late))
    return ssd


def continuum_species(rg_start, rg_end, center_start, center_end, n=40, envelope=None, sigma=6.0,
                      height=2.0, mass=1.0, shape="sphere", shape_arg_start=None, shape_arg_end=None, **species_kwargs):
    """Species that sample a continuous distribution: Rg changes smoothly along the elution.

    ``n`` species with Gaussian elution (``sigma`` frames) whose centres are spread uniformly over
    ``[center_start, center_end]``; the radius of gyration (and, if given, the shape parameter) changes
    linearly from the first to the last centre. For a known-truth benchmark of "distinct species or a
    continuum?" (use ``n`` large enough that neighbouring centres are much closer than ``sigma``).

    Amplitude convention: the amplitudes are scaled so that the *summed* elution profile follows
    ``height * envelope(centre)``, i.e. its maximum is about ``height`` (times ``mass``) whatever ``n`` and
    ``sigma`` are (the sum of Gaussians spaced ``d`` apart is ``amp * sigma * sqrt(2 pi) / d``).

    Parameters
    ----------
    rg_start, rg_end : float
        Radius of gyration at the first and the last centre.
    center_start, center_end : float
        Elution centres (XR frames) of the first and the last species.
    n : int, optional
    envelope : callable, optional
        ``envelope(centres)`` returns the relative weights (maximum about 1); default a Gaussian at the
        middle of the range with a standard deviation of 27.5 % of its width.
    sigma : float, optional
        Elution sigma of each species in frames (default 6).
    height : float, optional
        Height of the summed elution profile at the envelope maximum (default 2).
    mass : float, optional
    shape : str or callable, optional
        As for :class:`Species`.
    shape_arg_start, shape_arg_end : float, optional
        Shape parameter (ellipsoid axial ratio, cylinder length/radius) at the first and the last centre.
    **species_kwargs
        Passed to every :class:`Species` (``eps280``, ``na``, ``turb``).

    Returns
    -------
    list of Species
    """
    centres = np.linspace(center_start, center_end, n)
    if envelope is None:
        mid, span = 0.5*(center_start + center_end), abs(center_end - center_start)
        envelope = lambda c: np.exp(-0.5*((c - mid)/(0.275*span))**2)
    spacing = abs(centres[1] - centres[0])
    amp = height*spacing/(sigma*np.sqrt(2*np.pi))*np.asarray(envelope(centres), dtype=float)
    t = np.linspace(0.0, 1.0, n)
    rg = rg_start + (rg_end - rg_start)*t
    if shape_arg_start is None:
        arg = [None]*n
    else:
        arg = shape_arg_start + ((shape_arg_start if shape_arg_end is None else shape_arg_end) - shape_arg_start)*t
    return [Species(amp=float(a), center=float(c), sigma=sigma, mass=mass, rg=float(r), shape=shape,
                    shape_arg=None if x is None else float(x), **species_kwargs)
            for a, c, r, x in zip(amp, centres, rg, arg)]
