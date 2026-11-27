"""
    Guinier.RgConventions.py

    The apparent Rg of a profile with an interparticle effect depends on which Guinier interval is used (molass-library#419; molass-researcher
    experiment 66g): a fit that starts at the lowest q is depressed by the repulsion, one that starts higher can be raised. ``rg_conventions``
    returns the Rg of the library's adaptive interval and of a fixed ``q Rg < 1.3`` fit started at the lowest q, with the intervals, so the spread
    is visible at a glance.
"""
import numpy as np

QRG_MAX = 1.3


def fixed_guinier_fit(q, I, qrg_max=QRG_MAX, rg0=30.0, n_iter=5):
    """Iterative Guinier fit from the lowest q: the points with ``q*Rg < qrg_max`` and ``I > 0``, unweighted, repeated ``n_iter`` times with the new Rg.

    Returns a dict with ``Rg``, ``I0``, ``min_q``, ``max_q``, ``n_points``, ``qrg_max``; ``Rg`` and ``I0`` are NaN when the fit fails (fewer than 5 points,
    or a non-negative slope).
    """
    q = np.asarray(q, dtype=float)
    I = np.asarray(I, dtype=float)
    rg = rg0
    failed = dict(Rg=np.nan, I0=np.nan, min_q=None, max_q=None, n_points=0, qrg_max=None)
    for _ in range(n_iter):
        m = (q * rg < qrg_max) & (I > 0)
        if m.sum() < 5:
            return {**failed, 'n_points': int(m.sum())}
        slope, icpt = np.polyfit(q[m] ** 2, np.log(I[m]), 1)
        if slope >= 0:
            return {**failed, 'n_points': int(m.sum())}
        rg = float(np.sqrt(-3 * slope))
    return dict(Rg=rg, I0=float(np.exp(icpt)), min_q=float(q[m].min()), max_q=float(q[m].max()), n_points=int(m.sum()), qrg_max=float(q[m].max() * rg))


class RgConventions(dict):
    """The Rg of one profile under several Guinier conventions (a ``dict``: name -> dict of ``Rg``, ``I0``, ``min_q``, ``max_q``, ``n_points``,
    ``qrg_max``, ``score`` (the adaptive fit only), ``rg_source``). ``spread`` is the largest minus the smallest Rg; the ``repr`` is a table."""

    @property
    def spread(self):
        rgs = [v['Rg'] for v in self.values() if v['Rg'] is not None and np.isfinite(v['Rg'])]
        return float(max(rgs) - min(rgs)) if rgs else float('nan')

    def __repr__(self):
        lines = [f"{'convention':<28}{'Rg (A)':>8}  {'q range (1/A)':<17}{'points':>6}  {'q*Rg max':>8}  note"]
        for name, v in self.items():
            q_range = f"{v['min_q']:.4f}-{v['max_q']:.4f}" if v['min_q'] is not None else "-"
            qrg = f"{v['qrg_max']:.2f}" if v['qrg_max'] is not None else "-"
            note = []
            if v.get('rg_source') not in (None, 'legacy'):
                note.append(f"source {v['rg_source']}")
            if v.get('score') is not None:
                note.append(f"score {v['score']:.2f}" + (" (low)" if v.get('low_score') else ""))
            lines.append(f"{name:<28}{v['Rg']:>8.2f}  {q_range:<17}{v['n_points']:>6}  {qrg:>8}  {', '.join(note)}")
        lines.append(f"spread = {self.spread:.2f} A")
        return "\n".join(lines)


def rg_conventions(q, I, e=None, qrg_max=QRG_MAX):
    """Rg of the profile ``I(q)`` under two conventions, with the intervals used.

    Parameters
    ----------
    q, I : array-like
        The profile.
    e : array-like or None
        The error of ``I`` (the adaptive estimator needs a third column; ``None`` gives it unit errors, which it uses only for weights).
    qrg_max : float
        The ``q*Rg`` limit of the fixed fit (1.3).

    Returns
    -------
    RgConventions
        ``'adaptive (RgEstimator)'``: the library's estimator with its own interval; ``'from lowest q (q*Rg < 1.3)'``: the fixed fit started at the lowest q.

    Example
    -------
    ::

        from molass.Guinier import rg_conventions
        print(rg_conventions(q, A, Ae))
    """
    from molass.Guinier.RgEstimator import RgEstimator
    q = np.asarray(q, dtype=float)
    I = np.asarray(I, dtype=float)
    e = np.ones_like(I) if e is None else np.asarray(e, dtype=float)
    est = RgEstimator(np.array([q, I, e]).T)
    iv = est._interval()
    adaptive = dict(Rg=float(est.Rg) if est.Rg is not None else np.nan, I0=float(est.Iz) if getattr(est, 'Iz', None) is not None else np.nan,
                    min_q=iv['min_q'], max_q=iv['max_q'], n_points=iv['n_points'] or 0, qrg_max=iv['qrg_max'],
                    score=float(est.score) if est.score is not None else None, low_score=est.low_score, rg_source=est.rg_source)
    out = RgConventions()
    out['adaptive (RgEstimator)'] = adaptive
    out[f'from lowest q (q*Rg < {qrg_max:g})'] = fixed_guinier_fit(q, I, qrg_max=qrg_max)
    return out
