"""
    Testing.Sample4Like.py

    The simulated replacement of the former real SAMPLE4 (molass-library#379): known-truth SEC-SAXS data with
    fold/unfold variations (a folded core with a disordered Gaussian-chain tail, Pedersen 1997 item 25), written with
    the geometry, instrument error and actual scatter of the real SAMPLE4.

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
"""
import numpy as np

from .Simulator import Species, continuum_species, simulate_ssd, tail_shape, fold_unfold_shape, UV_SCALE
from molass.Kratky.FormFactors import fold_unfold_Rg

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

# Stated error of the real SAMPLE4 (median over frames): the first 41 points by index, then by q.
_E_IDX = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40])
_E_LOW = 1e-4*np.array([146.2, 99.3, 77.8, 50.4, 36.3, 30.6, 24.8, 21.2, 19.7, 17.7, 16.4, 15.8, 14.7,
                        14.5, 13.5, 13.1, 12.8, 12.4, 11.6, 11.2, 11.2, 11.1, 10.4, 9.9, 9.7, 9.7, 9.8])
_E_QNODES = np.linspace(0.024, 0.390, 22)
_E_NODES = 1e-4*np.array([9.79, 7.36, 6.94, 5.97, 5.21, 4.75, 4.47, 4.08, 3.86, 3.56, 3.25,
                          3.12, 2.95, 2.81, 2.71, 2.65, 2.5, 2.36, 2.24, 2.14, 2.08, 2.15])
# Actual scatter / stated error of the real data at the first ten points (0.02-0.07 at the first three).
_RATIO_FIRST = np.array([0.02, 0.04, 0.07, 0.56, 0.72, 0.75, 0.82, 0.71, 0.88, 0.82])


def error_profile():
    """Stated XR error per q-point (rises steeply at the smallest angles and at the last points, as measured)."""
    e = np.exp(np.interp(QV, _E_QNODES, np.log(_E_NODES)))
    e[:41] = np.exp(np.interp(np.arange(41), _E_IDX, np.log(_E_LOW)))
    e[-3:] *= np.array([1.0, 3.0, 13.5])
    return e


def noise_ratio():
    """Actual scatter relative to the stated error: far less at the first points, about 0.92 elsewhere.

    With the stated error used as noise the first points dominate the noise and the rank-3 denoising of
    ``quick_decomposition`` collapses the Rg of all components to one value."""
    r = np.full(len(QV), 0.92)
    r[:len(_RATIO_FIRST)] = _RATIO_FIRST
    r[-1] = 0.33
    return r


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


def simulate_sample4_like(kind="tails3", noise=1.0, seed=0):
    """Simulated data with the geometry, error and scatter of the real SAMPLE4 (see the module docstring)."""
    return simulate_ssd(sample4_like_species(kind), noise=noise, seed=seed, slope=SLOPE, intercept=INTERCEPT,
                        qv=QV, wv=WV, xr_frames=XR_FRAMES, uv_frames=UV_FRAMES,
                        xr_sigma=error_profile(), xr_noise_ratio=noise_ratio(), uv_sigma=SIGMA_UV, trimmed=False)
