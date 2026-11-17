"""
    SEC.Models.MatchCurves.py

    ``upgrade(model, match_curves=True)`` (molass-library#395).

    A plain ``upgrade()`` estimates the column parameters of the new model again from peak
    positions, widths and Rg; the fitted shapes of the source (EGH) curves do not carry over,
    so the new components can start quite different from them. Here the parameters of the new
    components are fitted by least squares to the component curves of the source
    decomposition (shared column parameters and per-component parameters together), so that
    the new model starts near the source solution. The result is a start for an optimization,
    not a fit of the model to the data: the data are fitted by ``optimize_rigorously()``.

    Available for the GRM and LKM models.
"""
import numpy as np
from scipy.optimize import least_squares

MODELS = ('GRM', 'LKM')


def check_model(model):
    if str(model).upper() not in MODELS:
        raise NotImplementedError(
            f"match_curves=True is available for {', '.join(MODELS)}, not {model!r}: "
            "use upgrade() without it (a fresh estimate)")


def _source_curves(source_ccurves, x):
    return np.array([np.asarray(cc.get_y(x), dtype=float) for cc in source_ccurves])


class _Adapter:
    """What the fit needs of a model: start vector, bounds and how to build the curves from a vector."""

    def __init__(self, p0, lower, upper, build):
        self.p0, self.lower, self.upper, self.build = p0, lower, upper, build


def _grm_adapter(new_ccurves, x):
    from molass.SEC.Models.GrmComponentCurve import GrmComponentCurve
    n = len(new_ccurves)
    c0 = new_ccurves[0]
    R_p, D_eff, F = c0.R_p, c0.D_eff, c0.F_ratio
    # a_star follows R (R = 1 + F * a_star): keep the offset the estimator chose
    a_off = [cc.a_star - (cc.R - 1.0) / F for cc in new_ccurves]
    rgs = [cc.rg for cc in new_ccurves]
    t_injs = [cc.t_inj for cc in new_ccurves]
    # [Pe, t0, then R_i, k_ext_i, c_inj_i per component], positive quantities in log scale
    p0 = [np.log(c0.Pe), np.log(c0.t0)]
    lower = [np.log(1.0), np.log(max(1e-3, 0.05 * c0.t0))]
    upper = [np.log(1e5), np.log(max(1.0, 2.0 * x[-1]))]
    for cc in new_ccurves:
        p0 += [np.log(cc.R - 1.0), np.log(cc.k_ext), np.log(cc.c_inj)]
        lower += [np.log(1e-3), np.log(1e-8), np.log(1e-12)]
        upper += [np.log(1e3), np.log(1e3), np.log(1e12)]

    def build(p):
        Pe, t0 = np.exp(p[0]), np.exp(p[1])
        curves = []
        for i in range(n):
            R = 1.0 + np.exp(p[2 + 3 * i])
            curves.append(GrmComponentCurve(
                x, Pe, t0, R_p, D_eff, (R - 1.0) / F + a_off[i], F,
                k_ext=np.exp(p[3 + 3 * i]), R=R, c_inj=np.exp(p[4 + 3 * i]), rg=rgs[i], t_inj=t_injs[i]))
        return curves

    return _Adapter(np.array(p0), np.array(lower), np.array(upper), build)


def _lkm_adapter(new_ccurves, x):
    from molass.SEC.Models.LkmComponentCurve import LkmComponentCurve
    n = len(new_ccurves)
    c0 = new_ccurves[0]
    rgs = [cc.rg for cc in new_ccurves]
    t_injs = [cc.t_inj for cc in new_ccurves]
    p0 = [np.log(c0.Pe), np.log(c0.t0)]
    lower = [np.log(1.0), np.log(max(1e-3, 0.05 * c0.t0))]
    upper = [np.log(1e5), np.log(max(1.0, 2.0 * x[-1]))]
    for cc in new_ccurves:
        p0 += [np.log(cc.R - 1.0), np.log(cc.k_MT), np.log(cc.c_inj)]
        lower += [np.log(1e-3), np.log(1e-8), np.log(1e-12)]
        upper += [np.log(1e3), np.log(1e8), np.log(1e12)]

    def build(p):
        Pe, t0 = np.exp(p[0]), np.exp(p[1])
        return [LkmComponentCurve(
                    x, Pe, t0, k_MT=np.exp(p[3 + 3 * i]), R=1.0 + np.exp(p[2 + 3 * i]),
                    c_inj=np.exp(p[4 + 3 * i]), rg=rgs[i], t_inj=t_injs[i])
                for i in range(n)]

    return _Adapter(np.array(p0), np.array(lower), np.array(upper), build)


_ADAPTERS = {'GRM': _grm_adapter, 'LKM': _lkm_adapter}


def match_ccurves(model, source_ccurves, new_ccurves, x, max_nfev=200, debug=False):
    """Fit the parameters of ``new_ccurves`` (one model) to the curves of ``source_ccurves``.

    Parameters
    ----------
    model : str
        ``'GRM'`` or ``'LKM'``.
    source_ccurves : list of ComponentCurve
        The component curves to match (e.g. those of the EGH decomposition).
    new_ccurves : list of ComponentCurve
        The estimated curves of the new model: the start of the fit.
    x : array
        The frame axis the curves are compared on.
    max_nfev : int, optional
        Maximum number of evaluations of the residuals.

    Returns
    -------
    ccurves : list of ComponentCurve
        The fitted curves; the start ones if the fit did not improve on them.
    info : dict
        ``start_error`` and ``error`` (root mean square difference to the source curves relative to
        the maximum of their sum), ``improved`` and ``nfev``.
    """
    check_model(model)
    if len(source_ccurves) != len(new_ccurves):
        raise ValueError(f"{len(source_ccurves)} source curves but {len(new_ccurves)} new ones")
    x = np.asarray(x, dtype=float)
    target = _source_curves(source_ccurves, x)
    scale = float(np.max(target.sum(axis=0))) or 1.0
    adapter = _ADAPTERS[str(model).upper()](new_ccurves, x)

    def residuals(p):
        curves = adapter.build(p)
        r = np.concatenate([(cc.get_y(x) - t) for cc, t in zip(curves, target)]) / scale
        return np.nan_to_num(r, nan=1e3, posinf=1e3, neginf=-1e3)

    def error(r):
        return float(np.sqrt(np.mean(r ** 2)))

    p0 = np.clip(adapter.p0, adapter.lower + 1e-9, adapter.upper - 1e-9)
    start_error = error(residuals(p0))
    # diff_step: the parameters are logarithms, often near 0, and the default step is relative to |p|: far too
    # small there (the fit then stalls at a local rms of 0.02 where 1e-4 recovers exactly)
    result = least_squares(residuals, p0, bounds=(adapter.lower, adapter.upper), diff_step=1e-4, max_nfev=max_nfev)
    final_error = error(result.fun)
    improved = bool(np.isfinite(final_error) and final_error < start_error)
    if debug:
        print(f"match_curves({model}): error {start_error:.4g} -> {final_error:.4g} in {result.nfev} evaluations")
    ccurves = adapter.build(result.x) if improved else list(new_ccurves)
    return ccurves, dict(start_error=start_error, error=final_error if improved else start_error,
                         improved=improved, nfev=int(result.nfev))
