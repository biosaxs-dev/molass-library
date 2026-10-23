"""
LowRank.ExportDecomposition.py

Implementation of :meth:`Decomposition.export`, which writes component
profiles together with the curves needed to reproduce the decomposition
figures or to continue the analysis in other tools (molass-library#319).

Column names are ASCII, start with a letter, use only letters, digits and
``_`` and are at most 31 characters long, so that the files also load
cleanly in IGOR, Origin, Excel and pandas.
"""
import json
import os
import datetime
import numpy as np

FORMATS = ('dat', 'csv')


def _write_table(folder, stem, names, columns, fmt, written):
    """Write equal-length 1-D ``columns`` as ``<folder>/<stem>.<fmt>``."""
    path = os.path.join(folder, f"{stem}.{fmt}")
    data = np.column_stack([np.asarray(c, dtype=float) for c in columns])
    if fmt == 'csv':
        np.savetxt(path, data, delimiter=',', header=','.join(names), comments='')
    else:
        np.savetxt(path, data, header=' '.join(names), comments='# ')
    written.append(path)


def _finite_or_none(value):
    if value is None:
        return None
    value = float(value)
    return value if np.isfinite(value) else None


def export_decomposition_impl(self, folder, fmt='dat', rgcurve=None,
                              compute_rg_curve=False, debug=False):
    """See :meth:`molass.LowRank.Decomposition.Decomposition.export`."""
    if fmt not in FORMATS:
        raise ValueError(f"fmt must be one of {FORMATS}, got {fmt!r}")

    os.makedirs(folder, exist_ok=True)
    n = self.num_components
    written = []
    skipped = {}

    # --- XR component profiles: same files as export_xr_components() for 'dat'
    xr_components = self.get_xr_components(debug=debug)
    for i, comp in enumerate(xr_components):
        if fmt == 'dat':
            path = os.path.join(folder, f"component_{i + 1}.dat")
            np.savetxt(path, comp.get_jcurve_array())
            written.append(path)
        else:
            arr = comp.get_jcurve_array()
            _write_table(folder, f"component_{i + 1}", ['q', 'intensity', 'error'],
                         [arr[:, 0], arr[:, 1], arr[:, 2]], fmt, written)

    # --- XR elution curves
    _, xrC, _, _ = self.get_xr_matrices(debug=debug)
    frames = np.asarray(self.xr_icurve.x)
    total = np.asarray(self.xr_icurve.y)
    comps = [xrC[i, :] for i in range(n)]
    xr_sum = np.sum(comps, axis=0)
    names = ['frame', 'xr_total'] + [f"comp{i + 1}" for i in range(n)] + ['xr_sum', 'xr_residual']
    _write_table(folder, 'xr_elution', names,
                 [frames, total] + comps + [xr_sum, total - xr_sum], fmt, written)

    # --- UV elution curves and component spectra
    if self.uv is None or self.uv_ccurves is None:
        skipped['uv'] = 'no UV data or UV decomposition'
        uv_components = None
    else:
        _, uvC, uvP, _ = self.get_uv_matrices(debug=debug)
        uv_frames = np.asarray(self.uv_icurve.x)
        uv_total = np.asarray(self.uv_icurve.y)
        uv_comps = [uvC[i, :] for i in range(n)]
        uv_sum = np.sum(uv_comps, axis=0)
        names = ['frame', 'uv_total'] + [f"comp{i + 1}" for i in range(n)] + ['uv_sum', 'uv_residual']
        _write_table(folder, 'uv_elution', names,
                     [uv_frames, uv_total] + uv_comps + [uv_sum, uv_total - uv_sum], fmt, written)
        names = ['wavelength'] + [f"comp{i + 1}" for i in range(n)]
        _write_table(folder, 'uv_spectra', names,
                     [self.uv.wv] + [uvP[:, i] for i in range(n)], fmt, written)

    # --- Guinier results per component
    guinier = []
    for i in range(n):
        try:
            g = xr_components[i].get_guinier_object()
        except Exception as exc:
            if debug:
                print(f"Guinier object failed for component {i + 1}: {exc!r}")
            g = None
        guinier.append(g)

    def _attr(g, name):
        v = getattr(g, name, None) if g is not None else None
        return float('nan') if v is None else float(v)

    _write_table(folder, 'guinier',
                 ['component', 'rg', 'i0', 'q_min', 'q_max', 'score'],
                 [np.arange(1, n + 1), [_attr(g, 'Rg') for g in guinier],
                  [_attr(g, 'Iz') for g in guinier], [_attr(g, 'min_q') for g in guinier],
                  [_attr(g, 'max_q') for g in guinier], [_attr(g, 'score') for g in guinier]],
                 fmt, written)

    # --- Rg curve (per frame); computing it is slow, so only use it when cheap
    if rgcurve is None and (compute_rg_curve or self.has_rg_curve):
        rgcurve = self.get_rg_curve()
    if rgcurve is None:
        skipped['rg_curve'] = 'not computed; pass rgcurve= or compute_rg_curve=True'
    else:
        _write_table(folder, 'rg_curve', ['frame', 'rg', 'score'],
                     [rgcurve.indeces, rgcurve.rgvalues, rgcurve.scores], fmt, written)

    # --- Summary
    from molass import __version__
    summary = {
        'molass_version': __version__,
        'created': datetime.datetime.now().isoformat(timespec='seconds'),
        'format': fmt,
        'num_components': n,
        'model': getattr(self, 'model', None),
        'method_label': self.method_label,
        'xr_ranks': None if self.xr_ranks is None else [int(r) for r in self.xr_ranks],
        'uv_ranks': None if self.uv_ranks is None else [int(r) for r in self.uv_ranks],
        'sv': _finite_or_none(getattr(self, 'sv', None)),
        'fv': _finite_or_none(getattr(self, 'fv', None)),
        'xr_frame_range': [int(self.xr.jv[0]), int(self.xr.jv[-1])],
        'q_range': [float(self.xr.qv[0]), float(self.xr.qv[-1])],
        'components': [
            {
                'index': i + 1,
                'rg': _finite_or_none(getattr(guinier[i], 'Rg', None)),
                'proportion': float(p),
                'uv_scale': None if self.uv_ccurves is None
                            else _finite_or_none(self.uv_ccurves[i].scale),
            }
            for i, p in enumerate(self.get_proportions())
        ],
        'files': [os.path.basename(p) for p in written],
        'skipped': skipped,
    }
    if self.uv is not None:
        summary['wavelength_range'] = [float(self.uv.wv[0]), float(self.uv.wv[-1])]
    path = os.path.join(folder, 'summary.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(summary, fh, indent=2, default=str)
        fh.write('\n')
    written.append(path)
    return written
