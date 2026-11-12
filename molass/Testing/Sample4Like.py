"""
    Testing.Sample4Like.py

    The simulated replacement of the former real SAMPLE4 (molass-library#379): known-truth SEC-SAXS data with
    fold/unfold variations (a folded core with a disordered Gaussian-chain tail, Pedersen 1997 item 25) with the
    photon-counting noise of Sedlak et al. (2017) (:mod:`molass.SAXS.ErrorModel`, molass-library#390, #391), on the
    geometry of the real SAMPLE4 (q grid, frames, mapping, intensity level) that it replaces. The measured error of that
    data set is not used.

    ``simulate_sample4_like(kind)`` returns a ``SecSaxsData`` (not trimmed, so that ``trimmed_copy()`` works as on
    measured data) whose truth is in ``ssd.simulation_truth``. The kinds are

    ``"tails3"``                  three overlapping species with tails of different share: the SAMPLE4 replacement
                                  (peaks, widths, areas and Rg of the three-component decomposition of the real data)
    ``"tail_continuum"``          the same family as a continuum (50 species, Rg falling along the elution)
    ``"fold_unfold_continuum"``   a high-contrast continuum: fast-exchange mix of a folded and an unfolded state whose
                                  unfolded fraction falls along the elution (Rg 52 to 26 A)
    ``"fold_unfold_discrete"``    three discrete fold/unfold species (a control that a diagnostic should call discrete)

    The Rg of a species is its true radius of gyration; Guinier fits of a sphere-plus-tail profile at q*Rg <= 1.3
    come out about 6 % lower. All kinds use the same elution geometry (XR frames 0-219, peak near frame 82).

    Noise: the standard error follows :func:`molass.SAXS.ErrorModel.sedlak_sigma` frame by frame and is also the
    stated error (``ssd.xr.E``). ``scale`` is the count level of the strongest frame at the first q point
    (``NOISE_SCALE``); the relative error goes as ``1 / sqrt(scale)``. The model is statistical only: unlike measured
    data the stated error has no rise at the first and last q points.
"""
import numpy as np
from functools import partial

from .Simulator import Species, continuum_species, simulate_ssd, tail_shape, fold_unfold_shape, UV_SCALE
from molass.Kratky.FormFactors import fold_unfold_Rg
from molass.SAXS.ErrorModel import sedlak_sigma

KINDS = ("tails3", "tail_continuum", "fold_unfold_continuum", "fold_unfold_discrete")

# Geometry of the real SAMPLE4: 773 q-points, 220 XR frames, 318 wavelengths, 442 UV frames.
QV = np.linspace(0.00727043, 0.407538668, 773)
WV = np.linspace(200.219, 450.758, 318)
XR_FRAMES = np.arange(220)
UV_FRAMES = np.arange(442)
SLOPE, INTERCEPT = 1.98, 0.0          # UV peak frame 168 against XR peak frame 85
HEIGHT = 0.078                          # maximum intensity at the smallest angles
A280 = 0.40                             # UV absorbance at the peak (280 nm)
SIGMA_UV = 6.0e-4                       # noise of the UV baseline of the real data
NOISE_SCALE = 30.0                      # counts of the strongest frame at the first q point; about the noise level of the
                                        # measured SAMPLE4 (100 is the synchrotron value of Sedlak et al. 2017, less noise)


def _eps280():
    return A280/(UV_SCALE*HEIGHT)


def _shoulder_envelope(c):
    g = lambda m, s: np.exp(-0.5*((c - m)/s)**2)
    return g(82.0, 4.5) + 0.50*g(100.0, 13.0) + 0.10*g(125.0, 12.0)


def tails3_species(centres=(81.0, 95.0, 115.0), sigmas=(6.5, 8.0, 10.0), area_fractions=(0.47, 0.33, 0.20),
                   rgs=(28.6, 26.7, 25.1), R=27.0, rg_c=18.0):
    """Three overlapping species, folded core with a tail (:func:`tail_shape`) of different mass share."""
    shape = tail_shape(R, rg_c)
    amps = np.asarray(area_fractions)/(np.asarray(sigmas)*np.sqrt(2*np.pi))
    species = [Species(amp=float(a), center=float(c), sigma=float(s), mass=1.0, rg=float(r), shape=shape,
                       eps280=_eps280())
               for a, c, s, r in zip(amps, centres, sigmas, rgs)]
    peak = sum(s.elution(XR_FRAMES) for s in species).max()
    for s in species:
        s.amp *= HEIGHT/peak
    return species


def tail_continuum_species(rg_start=30.6, rg_end=25.0, R=27.0, rg_c=18.0, n=50, sigma=5.0):
    return continuum_species(rg_start, rg_end, 66.0, 140.0, n=n, envelope=_shoulder_envelope, sigma=sigma,
                             height=HEIGHT, shape=tail_shape(R, rg_c), eps280=_eps280())


def fold_unfold_continuum_species(rg_start=52.0, rg_end=26.0, rg_fold=20.0, rg_unfold=55.0, n=50, sigma=5.0):
    return continuum_species(rg_start, rg_end, 66.0, 140.0, n=n, envelope=_shoulder_envelope, sigma=sigma,
                             height=HEIGHT, shape=fold_unfold_shape(rg_fold, rg_unfold), eps280=_eps280())


def fold_unfold_discrete_species(centres=(74.0, 96.0, 122.0), f_unfold=(0.9, 0.5, 0.1), amps=(1.0, 0.8, 0.6),
                                 sigma=7.0, rg_fold=20.0, rg_unfold=55.0):
    shape = fold_unfold_shape(rg_fold, rg_unfold)
    return [Species(amp=HEIGHT*a, center=c, sigma=sigma, mass=1.0, rg=float(fold_unfold_Rg(rg_fold, rg_unfold, f)),
                    shape=shape, eps280=_eps280())
            for a, c, f in zip(amps, centres, f_unfold)]


def sample4_like_species(kind="tails3"):
    """The species of ``simulate_sample4_like(kind)``."""
    if kind == "tails3":
        return tails3_species()
    if kind == "tail_continuum":
        return tail_continuum_species()
    if kind == "fold_unfold_continuum":
        return fold_unfold_continuum_species()
    if kind == "fold_unfold_discrete":
        return fold_unfold_discrete_species()
    raise ValueError(f"unknown kind {kind!r}; use one of {KINDS}")


def simulate_sample4_like(kind="tails3", noise=1.0, seed=0, scale=NOISE_SCALE):
    """Simulated data on the geometry of the real SAMPLE4 with the Sedlak et al. (2017) noise (see the module docstring).

    ``noise`` multiplies the noise and the stated error (0 gives noise-free data), ``scale`` is the count level of the
    error model."""
    return simulate_ssd(sample4_like_species(kind), noise=noise, seed=seed, slope=SLOPE, intercept=INTERCEPT,
                        qv=QV, wv=WV, xr_frames=XR_FRAMES, uv_frames=UV_FRAMES,
                        xr_error_model=partial(sedlak_sigma, scale=scale), uv_sigma=SIGMA_UV, trimmed=False)
