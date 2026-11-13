"""
    Testing.Tiny.py

    A small simulated data set for fast tests (molass-library#387): the whole chain
    ``trimmed_copy().corrected_copy()``, ``get_rg_curve()``, ``estimate_mapping()`` and
    ``quick_decomposition(num_components=2)`` takes about 6-9 s (``simulate_sample4_like()``: about 1 minute).
"""
from functools import partial

import numpy as np

from molass.Testing.Simulator import Species, simulate_ssd
from molass.Testing.Sample4Like import NOISE_SCALE
from molass.SAXS.ErrorModel import sedlak_sigma

TINY_QV = np.linspace(0.0143, 0.4268, 200)
TINY_WV = np.linspace(250.112, 449.959, 40)
TINY_XR_FRAMES = np.arange(80)
TINY_UV_FRAMES = np.arange(3, 122)
TINY_SPECIES = ((1.0, 25.0, 5.0, 1.0, 40.0), (1.0, 55.0, 5.0, 0.8, 25.0))     # amp, center, sigma, mass, rg


def tiny_species():
    """The two species of :func:`simulate_tiny` (see there for the truth)."""
    return [Species(amp=a, center=c, sigma=s, mass=m, rg=rg) for a, c, s, m, rg in TINY_SPECIES]


def simulate_tiny(noise=1.0, seed=0):
    """Two well separated species on a coarse grid, as a ready-made fixture for fast tests.

    Use it where a test needs real objects of the whole chain but not realistic data::

        ssd = simulate_tiny()
        corrected = ssd.trimmed_copy().corrected_copy()
        rg_curve = corrected.get_rg_curve()
        corrected.estimate_mapping()
        decomp = corrected.quick_decomposition(num_components=2)

    The five calls take about 9 s on first use in a process and 6 s after that (``simulate_sample4_like()``:
    about a minute), plus about 2 s to import molass; the data are
    200 q-values, 80 XR frames, 40 wavelengths and 119 UV frames, with the photon-counting error model of
    :func:`molass.SAXS.ErrorModel.sedlak_sigma`.

    Truth (``ssd.simulation_truth.species``)
    ----------------------------------------
    ============  ========  =====  ========  ====
    species       centre    sigma  mass      Rg
    ============  ========  =====  ========  ====
    1             frame 25  5      1.0       40 A
    2             frame 55  5      0.8       25 A
    ============  ========  =====  ========  ====

    The nominal UV->XR mapping is the one of SAMPLE1 (``uv = 1.4493 * xr + 3.464``). With the defaults
    the chain above leaves 197 q-values and 79 frames and ``quick_decomposition`` gives the Rg values
    42.0 and 25.3 A (``get_xr_components()[i].compute_rg()``; 45.4 / 25.5 and 41.0 / 25.7 for seeds 1 and 2);
    assert on them with a tolerance of about 10 %, not exactly.

    The grid is the smallest one tried: with fewer q-values (150) or frames the automatic trimming can
    fail, so do not shorten it; change ``noise`` or ``seed`` only after checking the chain.

    Parameters
    ----------
    noise : float, optional
        Scale of the noise and the stated error (1 is the level of :func:`simulate_sample4_like`); 0 gives noise-free data.
    seed : int, optional
        Seed of the noise.

    Returns
    -------
    ssd : SecSaxsData
        Not trimmed (``trimmed_copy()`` trims it), with ``ssd.simulation_truth``.
    """
    return simulate_ssd(tiny_species(), noise=noise, seed=seed,
                        qv=TINY_QV, wv=TINY_WV, xr_frames=TINY_XR_FRAMES, uv_frames=TINY_UV_FRAMES,
                        xr_error_model=partial(sedlak_sigma, scale=NOISE_SCALE), trimmed=False)
