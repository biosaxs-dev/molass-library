"""
    LowRank.SecondDirection.py

    ``decomposition.second_direction_report()`` (molass-library#417): what is the second direction of a rank-2 matrix? An interparticle effect (``M ~ A c + B c^2``, one
    species) and two overlapping species (``M ~ P1 c1 + P2 c2``) both give a rank-2 matrix with the same 2-dimensional subspace, so SRR, SCD and SNR2 cannot tell them
    apart. The difference is the structure inside the subspace: for an interparticle effect the second time row is exactly the square of the first. This module reads that
    structure from the data alone (no UV curve, no structure-factor model, no known concentration curve): an SVD of the row-whitened window and four indicators of the
    **time side** (molass-researcher experiment 67, ``experiments/67_second_direction/README.md``):

    * **SNR2**: is there a second direction above the noise? (the gate: below 3 nothing is read)
    * **closure** ``rho_min``: is there a time direction c(theta) in the 2-dimensional time subspace whose square also lies in it? (small for a c^2 term)
    * **CEF**: the share of the extra direction explained by the c^2 row of the first singular vector (near 1 for a c^2 term)
    * **parity**: the odd part (about the apex) of the extra time direction, minus that of c^2 (about 0 for a c^2 term, large for a shifted second species)
    * **hysteresis**: chi^2/dof of the profile difference between the rising and the falling side at equal concentration (about 1 for a c^2 term; the concentration axis is
      the first singular vector: a UV curve through the mapping is not usable, an offset of 2 frames already gives chi^2/dof 30-100)

    and a **baseline-direction flag** (SNR3 and the distance of the flat vector 1/e(q) from the top-2 / top-3 subspace): a flat additive error is a second direction with no
    c^2 structure and makes every time-side value read "not a c^2 term".

    The report shows evidence. The reference ranges are simulated values (experiment 67, stage A, noise x1.0, 20 draws per truth, runs with SNR2 > 3; hard-sphere and soft
    interparticle truths, species with a shift, species with a width change, composition drift) and are **provisional**: they are for orientation, not thresholds, and they were
    obtained at SNR2 of 8 and more. Validated on simulations and one real data set (SAMPLE3). **Not covered**: a monomer-dimer equilibrium has the same c^2 time structure
    and reads like an interparticle effect on the time side; the q side (where in q the extra signal sits) is left out because it was not robust to the region edges
    (molass-researcher#15).
"""
import numpy as np

Q_HI = 0.25                  # the window is q < Q_HI (1/Angstrom); the trimming has already removed the lowest q
FRAME_FRAC = 0.05            # default frames: above this fraction of the peak of the summed intensity
SNR2_GATE = 3.0              # below this, every indicator sits at its noise value (closure 0.24, CEF 0.4 for no second direction): nothing is read
HYST_LEVELS = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
HYST_Q = (0.01, 0.12)
BASELINE_LIKELY = 0.15       # d3 (or d2) below this: the flat vector is in the subspace (a ramp of 0.5 % of I0 gives 0.06-0.09)
BASELINE_POSSIBLE = 0.45     # below this: possible (0.1 % of I0 gives 0.3-0.4; the chain and cylinder without a ramp 0.5-0.7)

REFERENCE = {   # indicator -> group -> (low, high): lowest 10 % to highest 90 % over the truths of the group (experiment 67 stage A, noise x1.0, SNR2 > 3)
    'closure_rho_min': {'interparticle': (0.006, 0.041), 'width-only species': (0.051, 0.056), 'shifted species': (0.195, 0.233), 'composition drift': (0.175, 0.178)},
    'cef': {'interparticle': (0.971, 0.998), 'width-only species': (0.84, 0.867), 'shifted species': (0.0006, 0.137), 'composition drift': (0.031, 0.033)},
    'parity': {'interparticle': (-0.010, 0.019), 'width-only species': (0.091, 0.106), 'shifted species': (0.718, 0.929), 'composition drift': (0.588, 0.596)},
    'hysteresis': {'interparticle': (0.95, 1.04), 'width-only species': (1.21, 1.74), 'shifted species': (1.78, 864.0), 'composition drift': (28.0, 29.3)},
}
LABELS = {'closure_rho_min': 'closure rho_min', 'cef': 'CEF', 'parity': 'parity (odd w - odd c^2)', 'hysteresis': 'hysteresis chi2/dof'}


def _window(qv, M, E, frames):
    qv, M, E = (np.asarray(x, dtype=float) for x in (qv, M, E))
    if frames is None:
        tot = M.sum(axis=0)
        idx = np.where(tot >= FRAME_FRAC * tot.max())[0]
        fr = np.arange(idx.min(), idx.max() + 1)
    else:
        fr = np.arange(int(frames[0]), int(frames[1]))
    e_row = np.median(E, axis=1)
    qm = (qv < Q_HI) & np.isfinite(e_row) & (e_row > 0)
    if qm.sum() < 20 or len(fr) < 20:
        raise ValueError(f"the window is too small for the report ({int(qm.sum())} q rows below {Q_HI}, {len(fr)} frames; at least 20 of each)")
    X = (M / e_row[:, None])[np.ix_(qm, fr)]
    U, s, Vt = np.linalg.svd(X, full_matrices=False)
    return dict(X=X, fr=fr, qm=qm, U=U, s=s, Vt=Vt, e_row=e_row, M=M, E=E, qv=qv)


def _noise_edge(s, X, k):
    """Noise variance per element of the whitened window from the singular values beyond k, and the bulk edge (sqrt(m) + sqrt(N))^2."""
    m, N = X.shape
    tail = float(np.sum(s[k:] ** 2) / ((m - k) * (N - k)))
    return tail, tail * (np.sqrt(m) + np.sqrt(N)) ** 2


def _closure(V):
    """rho_min, theta_hat (degrees) over the non-negative directions c(theta) = cos v1 + sin v2: the part of c^2 outside span(v1, v2)."""
    best, bt = np.inf, float('nan')
    for deg in np.arange(0.0, 180.0, 0.5):
        th = np.deg2rad(deg)
        c = np.cos(th) * V[:, 0] + np.sin(th) * V[:, 1]
        if c.sum() < 0:
            c = -c
        if c.min() < -0.02 * c.max():
            continue
        c2 = c ** 2
        rho = float(np.linalg.norm(c2 - V @ (V.T @ c2)) / np.linalg.norm(c2))
        if rho < best:
            best, bt = rho, float(deg)
    return best, bt


def _resid_energy(X, C):
    Q, _ = np.linalg.qr(C.T)
    return float(np.sum((X - (X @ Q) @ Q.T) ** 2))


def _odd_fraction(x, apex, h):
    seg = x[apex - h: apex + h + 1]
    odd = (seg - seg[::-1]) / 2
    return float(np.sum(odd ** 2) / max(np.sum(seg ** 2), 1e-30))


def _crossing(c, lv, rising, apex):
    rng = range(apex - 1, -1, -1) if rising else range(apex, len(c) - 1)
    for a in rng:
        lo, hi = (c[a], c[a + 1]) if rising else (c[a + 1], c[a])
        if lo <= lv <= hi and c[a + 1] != c[a]:
            return a, (lv - c[a]) / (c[a + 1] - c[a])
    return None


def _hysteresis(M, E, c, qrows):
    """Mean over the levels of chi^2/dof of the profile difference between the falling and the rising frame of equal c (profiles interpolated in time)."""
    c = np.asarray(c, float) / np.max(c)
    apex = int(np.argmax(c))
    out = []
    for lv in HYST_LEVELS:
        r, f = _crossing(c, lv, True, apex), _crossing(c, lv, False, apex)
        if r is None or f is None:
            continue
        prof, var = [], []
        for a, w in (r, f):
            prof.append((1 - w) * M[qrows, a] + w * M[qrows, a + 1])
            var.append((1 - w) ** 2 * E[qrows, a] ** 2 + w ** 2 * E[qrows, a + 1] ** 2)
        out.append(float(np.mean((prof[1] - prof[0]) ** 2 / (var[0] + var[1]))))
    return float(np.mean(out)) if out else float('nan')


class SecondDirectionReport(dict):
    """The evidence of :func:`second_direction_report` (a ``dict``; the ``repr`` is a short text).

    Keys: ``snr2``, ``readable`` (SNR2 above the gate), ``window`` (``q_range``, ``frames``, ``n_rows``), ``baseline`` (``snr3``, ``d2``, ``d3``, ``flag``: ``'none'``, ``'possible'``
    or ``'likely'``, ``text``), ``time_side`` (indicator -> ``value``; empty when not readable), ``closure_theta``, ``reference`` (the provisional ranges per group) and ``notes``.
    """

    def __repr__(self):
        w = self['window']
        lines = [f"second direction report (window: q {w['q_range'][0]:.4f}-{w['q_range'][1]:.4f} 1/A, {w['n_rows']} rows; frames {w['frames'][0]}-{w['frames'][1] - 1})",
                 f"  SNR2 = {self['snr2']:.3g}" + ("" if self['readable'] else f": below {SNR2_GATE:g}, no second direction above the noise; nothing is read (every indicator sits at its noise value)"),
                 "  baseline direction: " + self['baseline']['text']]
        if self['readable']:
            lines.append("  time side (value | reference ranges: interparticle | width-only species | shifted species | composition drift):")
            for k, v in self['time_side'].items():
                ref = self['reference'][k]
                lines.append(f"    {LABELS[k]:<26}{v:>9.3g} | " + " | ".join(f"{lo:.3g} to {hi:.3g}" for lo, hi in (ref[g] for g in ref)))
            lines.append("  Reading guide (evidence, not a verdict): all four near the interparticle ranges: consistent with a pure c^2 term of one species (an interparticle effect, or "
                         "an association, which has the same time structure); away from them: another time profile (a second species, composition drift, aggregation, a baseline error).")
        for n in self['notes']:
            lines.append("  note: " + n)
        return "\n".join(lines)


def second_direction_report(qv, M, E, frames=None):
    """What is the second direction of the matrix (one species around its peak)? See the module docstring.

    Parameters
    ----------
    qv : array, shape (n_q,)
    M : array, shape (n_q, n_frames)
        The (trimmed, baseline-corrected) intensities.
    E : array, shape (n_q, n_frames)
        The stated error (needed: every q row is divided by its median error before the SVD).
    frames : (start, stop) or None
        The frames of the peak (``start <= frame < stop``); ``None``: the frames above 5 % of the peak of the summed intensity.

    Returns
    -------
    SecondDirectionReport
    """
    if E is None:
        raise ValueError("the second-direction report needs the stated error (E is None)")
    w = _window(qv, M, E, frames)
    X, fr, qm, U, s, Vt, M, E, qv = (w[k] for k in ('X', 'fr', 'qm', 'U', 's', 'Vt', 'M', 'E', 'qv'))
    m_, N_ = X.shape
    if len(s) < 5:
        raise ValueError("the window is too small for the report")
    tail3, edge3 = _noise_edge(s, X, 3)
    snr2 = float(s[1] ** 2 / edge3)
    tail4, edge4 = _noise_edge(s, X, 4)
    snr3 = float(s[2] ** 2 / edge4)
    f = 1.0 / w['e_row'][qm]
    f = f / np.linalg.norm(f)
    d = {k: float(np.linalg.norm(f - U[:, :k] @ (U[:, :k].T @ f))) for k in (2, 3)}
    dmin = min(d.values())
    flag = 'likely' if dmin < BASELINE_LIKELY else ('possible' if dmin < BASELINE_POSSIBLE else 'none')
    btext = {'none': "no flat (baseline-like) direction in the top-3 subspace",
             'possible': "a flat (baseline-like) direction may be present",
             'likely': "a flat (baseline-like) direction is present: the time-side values then read 'not a c^2 term'; correct the baseline first"}[flag]
    baseline = dict(snr3=snr3, d2=d[2], d3=d[3], flag=flag, text=f"{btext} (SNR3 {snr3:.3g}, d2 {d[2]:.2f}, d3 {d[3]:.2f}; floor about 0.1-0.2 % of I0)")
    readable = bool(snr2 > SNR2_GATE)
    notes = []
    time_side, theta = {}, float('nan')
    if readable:
        v1, v2 = Vt[0], Vt[1]
        if v1.sum() < 0:
            v1, v2 = -v1, -v2
        c = v1 / v1.max()
        rho, theta = _closure(np.stack([v1, v2], axis=1))
        svd2 = float(np.sum(s[2:] ** 2))
        base = _resid_energy(X, np.array([c]))
        cef = float((base - _resid_energy(X, np.array([c, c ** 2]))) / max(base - svd2, 1e-12))
        apex = int(np.argmax(c))
        h = min(apex, len(c) - 1 - apex)
        parity = float('nan')
        if h >= 5:
            cn = c / np.linalg.norm(c)
            wv = v2 - (v2 @ cn) * cn
            ref = c ** 2 - (c ** 2 @ cn) * cn
            parity = _odd_fraction(wv, apex, h) - _odd_fraction(ref, apex, h)
        c_full = np.zeros(M.shape[1])
        c_full[fr] = c
        qh = (qv >= HYST_Q[0]) & (qv < HYST_Q[1])
        hyst = _hysteresis(M, E, c_full, qh) / max(tail3, 1e-30)             # the noise scale (stated error too small or too large) divides out
        time_side = {'closure_rho_min': rho, 'cef': cef, 'parity': parity, 'hysteresis': hyst}
        if not np.isfinite(parity):
            notes.append("parity is not available: the peak window is too short around the apex")
            time_side.pop('parity')
        if snr2 < 10:
            notes.append(f"SNR2 is {snr2:.3g}: the reference ranges were obtained at SNR2 of 8 and more; closer to the noise closure rises and CEF falls toward their noise values (0.24 and 0.4)")
    if flag != 'none' and readable:
        notes.append("a baseline-like direction is flagged above: it can make any second direction read 'not a c^2 term'")
    return SecondDirectionReport(
        snr2=snr2, readable=readable, baseline=baseline, time_side=time_side, closure_theta=theta, reference={k: v for k, v in REFERENCE.items()},
        window=dict(q_range=(float(qv[qm][0]), float(qv[qm][-1])), frames=(int(fr[0]), int(fr[-1]) + 1), n_rows=int(qm.sum())), notes=notes)
