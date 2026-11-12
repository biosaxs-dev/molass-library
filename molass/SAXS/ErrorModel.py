"""
    SAXS.ErrorModel.py

    Photon-counting error model of SAXS profiles for simulated data (molass-library#390).

    S. M. Sedlak, L. K. Bruetzel and J. Lipfert, J. Appl. Cryst. 50 (2017) 621-630, "Quantitative evaluation of
    statistical errors in small-angle X-ray scattering measurements".

    Scattering and counting are Poisson processes, the buffer intensity is about constant over q, and sample and buffer
    are measured independently. With N(q) = k q pixels per q bin (eq. 9), the buffer intensity I_b = c I_s(q_arb) and the
    buffer-subtracted intensity I(q) (eqs. 4-8, 10):

        sigma^2(q) = [ I(q) + 2 c I(q_arb) / (1 - c) ] / (k q)                 (counts^2)

    Typical values (Table 1 and section 3.7 of the paper): k = 4500 A, c = 0.85, q_arb = 0.2 1/A and a profile scaled to
    about 100 counts for a synchrotron (``SYNCHROTRON``); c = 0.90 and about 10 counts for an in-house source
    (``IN_HOUSE``).

    Validity: the model is statistical only (the best case: no systematic error, no radiation damage, no
    detector artefact) and was validated by the authors for q = 0.05-0.35 1/A with one sample and one buffer exposure.
    Outside that range it is an extrapolation: below about 0.05 the buffer is not constant, and N(q) = k q holds for
    small angles only. Real reduced data may carry a larger stated error at the first and the last q points than the
    model gives; the model does not reproduce such instrument- or reduction-specific features.

    Any noise-free profile (or SEC-SAXS matrix) in arbitrary units can be given realistic noise by choosing ``scale``,
    the number of counts of the strongest frame at the first q point; the sigma returned is in the units of the input and
    can serve as the stated error of the simulated data.
"""
import numpy as np

SYNCHROTRON = dict(scale=100.0, k=4500.0, c=0.85, q_arb=0.2)
IN_HOUSE = dict(scale=10.0, k=4500.0, c=0.90, q_arb=0.2)


def sedlak_sigma(I, q, scale=100.0, k=4500.0, c=0.85, q_arb=0.2, n_buffer=1):
    """Standard error of the buffer-subtracted intensity after Sedlak et al. (2017), in the units of ``I``.

    Parameters
    ----------
    I : array-like, shape (nq,) or (nq, nframes)
        Noise-free intensity; negative values are treated as 0. For a matrix the strongest frame (largest sum)
        sets the count level and the buffer term, which is the same for all frames of a SEC run.
    q : array-like, shape (nq,)
        Scattering vector (1/A), positive.
    scale : float, optional
        Counts of the strongest frame at the first q point (default 100, the synchrotron value of the paper;
        10 for an in-house source). The relative error scales as ``1/sqrt(scale)``.
    k : float, optional
        Pixels per q bin are ``k * q`` (default 4500 A).
    c : float, optional
        Buffer intensity relative to the sample intensity at ``q_arb`` (``0 <= c < 1``; default 0.85).
    q_arb : float, optional
        Reference q of ``c`` (default 0.2 1/A); the buffer is assumed constant over q.
    n_buffer : int, optional
        Number of averaged buffer exposures. 1 is the paper's single sample and single buffer exposure; the buffer
        term becomes ``I_b (1 + 1/n_buffer)``.

    Returns
    -------
    sigma : ndarray, same shape as ``I``
    """
    I = np.asarray(I, dtype=float)
    q = np.asarray(q, dtype=float)
    if I.ndim not in (1, 2) or q.ndim != 1 or I.shape[0] != len(q):
        raise ValueError("I must have shape (nq,) or (nq, nframes) with q of shape (nq,)")
    if np.any(q <= 0):
        raise ValueError("q must be positive")
    if scale <= 0 or k <= 0 or n_buffer < 1:
        raise ValueError("scale and k must be positive and n_buffer at least 1")
    if not 0 <= c < 1:
        raise ValueError("c must satisfy 0 <= c < 1")
    frames = I if I.ndim == 2 else I[:, None]
    peak = np.clip(frames[:, np.argmax(frames.sum(axis=0))], 0, None)
    if not peak[0] > 0:
        raise ValueError("the strongest frame has no positive intensity at the first q point")
    to_counts = scale/peak[0]
    i_arb = np.interp(q_arb, q, peak)*to_counts
    buffer_counts = c*i_arb/(1.0 - c)*(1.0 + 1.0/n_buffer)
    var = (np.clip(frames, 0, None)*to_counts + buffer_counts)/(k*q)[:, None]
    sigma = np.sqrt(var)/to_counts
    return sigma if I.ndim == 2 else sigma[:, 0]


def add_sedlak_noise(I, q, seed=0, **kwargs):
    """Add Gaussian noise with the standard deviation of :func:`sedlak_sigma`.

    Returns
    -------
    noisy_I, sigma : ndarray, ndarray
        The noisy intensity and the sigma used (the natural stated error of the simulated data).
    """
    sigma = sedlak_sigma(I, q, **kwargs)
    rng = np.random.default_rng(seed)
    return np.asarray(I, dtype=float) + sigma*rng.standard_normal(sigma.shape), sigma
