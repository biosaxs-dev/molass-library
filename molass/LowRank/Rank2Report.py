"""
    LowRank.Rank2Report.py

    ``decomposition.rank2_report()`` (molass-library#420): one call for what the rank-2 (interparticle) correction did, per rank-2 component: the method and
    its options, the bound (K, sigma, cut-off), how much of the data the bound lets through (mean weight, violation fraction), what the curve refinement
    did, the Rg of the corrected and of the uncorrected profile under more than one convention, and the warnings (which are lost when ``warn=False`` or
    when the result is cached).
"""
import numpy as np


class Rank2Report(dict):
    """A ``dict`` keyed by the component index (rank-2 components only); each value is a dict. The ``repr`` is a short text that can be pasted into a status record."""

    def __repr__(self):
        if not len(self):
            return "Rank2Report: no rank-2 component"
        lines = []
        for k, r in self.items():
            lines.append(f"component {k}: {r['method']}" + (f", options {r['options']}" if r['options'] else ""))
            if r.get('note'):
                lines.append(f"  {r['note']}")
                continue
            if r['method'] == 'soft_bounded':
                lines.append(f"  bound: K = {r['K']:.3g}, sigma = {r['sigma']:.1f} A, L = {r['L']:g}, cut-off pi/R = {r['cutoff_q']:.4f} 1/A")
                lines.append(f"  data against bound: mean weight (1.5 <= q Rg <= 3.5) = {r['weight_mid']:.2f} (1 = all data, 0 = no correction), "
                             f"violation fraction = {r['violation_fraction']:.2f}")
                ref = r['refinement']
                lines.append("  curve refinement: " + ("off" if ref is None else
                             f"{'ended at a bound' if ref['at_bound'] else 'inside its bounds'}, largest change of the curve (peak = 1) = {ref['max_curve_change']:.3f}"))
            else:
                lines.append(f"  bound: K = {r['K']:.3g}, L = {r['L']:.3g}, R = {r['R']:.1f} A, cut-off pi/R = {r['cutoff_q']:.4f} 1/A"
                             f"{' (L at the penalty bound)' if r['L_penalized'] else ''}")
                lines.append(f"  clipped: band {r['clipped_fraction']['band']:.0%}, above the band {r['clipped_fraction']['above_b2']:.0%}; "
                             f"largest move into A(q) in the band {r['max_move_in_band']:.1%}")
            for name, conv in (("corrected", r['rg_corrected']), ("uncorrected (rank 1)", r['rg_uncorrected'])):
                lines.append(f"  Rg {name}: " + "; ".join(f"{n} {v['Rg']:.2f} A" + (f" (score {v['score']:.2f}{', low' if v.get('low_score') else ''})" if v.get('score') is not None else "")
                                                         for n, v in conv.items()) + f"; spread {conv.spread:.2f} A")
            imp = r['impact']
            lines.append("  impact: Rg " + "; ".join(f"{g['convention']} {g['uncorrected']:.2f} -> {g['corrected']:.2f} A ({g['change_pct']:+.1f} %)" for g in imp['rg']))
            sh = imp['shape']
            if sh is None:
                lines.append("  impact: the shape of A(q) against rank 1 could not be compared (too few points at high q)")
            else:
                lines.append(f"  impact: A(q) shape against rank 1 (normalised at q*Rg >= {sh['high_from']:g}, Rg = {sh['rg']:.1f} A): " + ", ".join(
                    f"{name} {v['median_pct']:+.1f} % (max {v['max_abs_pct']:.1f})" for name, v in sh['regions'].items() if v is not None))
            for f in r['findings']:
                lines.append(f"  finding [{f.code}]: {f.plain}")
                lines.append(f"    affects: {f.region}; check: {f.check}")
            if r['findings']:
                lines.append("  (the thresholds behind the findings are provisional; a finding is not a risk level)")
            else:
                lines.append("  no findings")
        return "\n".join(lines)


HIGH_FROM = 3.5          # q*Rg from which the profile is taken as unchanged by the correction (it fades out there)
REGIONS = (("Guinier", 0.0, 1.3), ("mid", 1.3, HIGH_FROM), ("high", HIGH_FROM, np.inf))


def profile_shape_change(qv, A_corrected, A_uncorrected, rg):
    """How much the correction changes the **shape** of A(q) against the uncorrected (rank 1) profile, per region of ``q*Rg``.

    The units of the two A(q) differ (the refined concentration curve changes the scale), so the ratio ``A_corrected / A_uncorrected`` is divided by its median
    over the high-q region (``q*Rg >= 3.5``), where the correction fades out; the change is that ratio minus 1. Returns ``None`` when the high-q region has
    fewer than 5 usable points, else a dict ``rg``, ``high_from`` and ``regions``: region name (``'Guinier'`` ``q*Rg < 1.3``, ``'mid'`` ``1.3 <= q*Rg < 3.5``, ``'high'``) ->
    ``dict(median_pct, max_abs_pct, n)`` (``None`` for an empty region).
    """
    qv, a, b = (np.asarray(x, float) for x in (qv, A_corrected, A_uncorrected))
    ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
    qrg = qv * rg
    ratio = np.full(len(qv), np.nan)
    ratio[ok] = a[ok] / b[ok]
    high = ok & (qrg >= HIGH_FROM)
    if high.sum() < 5:
        return None
    change = ratio / np.median(ratio[high]) - 1.0
    regions = {}
    for name, lo, hi in REGIONS:
        m = ok & (qrg >= lo) & (qrg < hi)
        regions[name] = None if not m.any() else dict(median_pct=float(np.median(change[m]) * 100), max_abs_pct=float(np.max(np.abs(change[m])) * 100), n=int(m.sum()))
    return dict(rg=float(rg), high_from=HIGH_FROM, regions=regions)


def build_rank2_report(decomp):
    """Build the :class:`Rank2Report` of a :class:`~molass.LowRank.Decomposition.Decomposition` (see ``Decomposition.rank2_report``)."""
    from molass.Guinier.RgConventions import rg_conventions
    from molass.LowRank.LowRankInfo import compute_lowrank_matrices

    report = Rank2Report()
    ranks = decomp.xr_ranks or [1] * decomp.num_components
    rank2 = [k for k, r in enumerate(ranks) if r == 2]
    if not rank2:
        return report
    xr = decomp.xr
    _M, _C, P, Pe = decomp.get_xr_matrices()                              # fills (or reuses the cache of) the diagnostics
    _M1, _C1, P1, Pe1 = compute_lowrank_matrices(xr.M, decomp.xr_ccurves, xr.E, [1] * decomp.num_components)
    method = decomp.rank2_method
    infos = decomp.soft_bounded_info if method == 'soft_bounded' else decomp.bounded_lrf_info
    for k in rank2:
        entry = dict(method=method, options=dict(decomp.rank2_options) if method == 'soft_bounded' else {})
        info = (infos or {}).get(k)
        if info is None:
            entry['note'] = "not corrected: no valid Rg seed for the bound (the profile of the first pass has no Guinier region)"
            report[k] = entry
            continue
        entry.update(K=float(info['K']), L=float(info['L']), cutoff_q=float(info['cutoff_q']), warnings=info.warnings_list())
        if method == 'soft_bounded':
            entry.update(sigma=float(info['sigma']), weight_mid=float(info['weight_mid']), violation_fraction=float(info['violation_fraction']))
            ref = info.get('refine')
            if info.get('c_refined') is None or ref is None:
                entry['refinement'] = None
            else:
                c_lib = np.asarray(decomp.xr_ccurves[k].get_xy()[1], float) / info['c_scale']
                entry['refinement'] = dict(at_bound=bool(ref.get('at_bound')), converged=ref.get('converged'),
                                           max_curve_change=float(np.max(np.abs(np.asarray(info['c_refined']) - c_lib))))
        else:
            entry.update(R=float(info['R']), L_penalized=bool(info['L_penalized']), clipped_fraction=info['clipped_fraction'],
                         max_move_in_band=float(info['max_move_in_band']))
        entry['rg_corrected'] = rg_conventions(xr.qv, P[:, k], Pe[:, k] if Pe is not None else None)
        entry['rg_uncorrected'] = rg_conventions(xr.qv, P1[:, k], Pe1[:, k] if Pe1 is not None else None)
        entry['findings'] = info.findings()
        rg_changes = [dict(convention=name, uncorrected=float(entry['rg_uncorrected'][name]['Rg']), corrected=float(v['Rg']),
                           change_pct=float((v['Rg'] / entry['rg_uncorrected'][name]['Rg'] - 1) * 100))
                      for name, v in entry['rg_corrected'].items() if name in entry['rg_uncorrected']]
        rg_region = next((v['Rg'] for v in entry['rg_corrected'].values() if np.isfinite(v['Rg'])), None)
        entry['impact'] = dict(rg=rg_changes, shape=None if rg_region is None else profile_shape_change(xr.qv, P[:, k], P1[:, k], rg_region))
        report[k] = entry
    return report
