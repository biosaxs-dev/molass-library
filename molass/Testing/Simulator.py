"""
    Testing.Simulator.py

    A known-truth SEC-SAXS simulator (molass-library#340): species with Gaussian elution,
    sphere-like scattering and UV spectra, and a UV->XR mapping, to verify analyses against
    the truth (mapping resolution, homogeneity, decompositions, ...).

    Model (SAMPLE1 geometry by default): ``I(q, f) = sum_i m_i c_i(f) P_i(q)`` and
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


@dataclass
class Species:
    """One species: Gaussian elution (``amp``, ``center`` and ``sigma`` in XR frames), scattering mass
    ``mass`` and radius of gyration ``rg``, UV extinction at 280 nm ``eps280``, nucleic-acid
    contribution ``na`` and turbidity ``turb`` of the UV spectrum."""
    amp: float
    center: float
    sigma: float
    mass: float
    rg: float
    eps280: float = 1.0
    na: float = 0.0
    turb: float = 0.01

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
        I += (s.mass * s.elution(xr_frames))[None, :] * sphere(qv, s.rg)[:, None]
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
