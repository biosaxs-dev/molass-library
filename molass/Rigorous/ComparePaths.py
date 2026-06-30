"""
    Rigorous.ComparePaths.py

    Side-by-side validation of `optimize_rigorously()` execution paths
    (subprocess vs in-process), introduced as Phase 2.5 of the
    split-architecture plan.  See
    ``molass-library/Copilot/DESIGN_split_optimizer_architecture.md``.

    Single-cell entry point for the `13h_split_architecture_validation`
    workflow:

        from molass.Rigorous import compare_optimization_paths

        result = compare_optimization_paths(
            decomp, rgcurve,
            method='NS', niter=20,
            paths=('subprocess', 'in_process'),
            trimmed_ssd=trimmed,
        )
        result.summary_table()
        result.plot_convergence()
        result.plot_components()
        result.assert_parity(fv_rtol=1e-2)

    Copyright (c) 2026, SAXS Team, KEK-PF
"""
import os
import time

import numpy as np


_PATH_ALIASES = {
    'subprocess': False,
    'subproc':    False,
    'sub':        False,
    'in_process': True,
    'inprocess':  True,
    'inproc':     True,
    'inp':        True,
}


def _resolve_path(name):
    """Map a path name to the ``in_process`` boolean."""
    try:
        return _PATH_ALIASES[name]
    except KeyError as e:
        raise ValueError(
            "Unknown path %r; expected one of %s"
            % (name, sorted(_PATH_ALIASES))
        ) from e


class PathResult:
    """Result of a single ``optimize_rigorously`` call inside a comparison.

    Attributes
    ----------
    label : str
        Path label (``'subprocess'`` or ``'in_process'``).
    in_process : bool
        Resolved ``in_process`` flag passed to ``optimize_rigorously``.
    analysis_folder : str
        Absolute path to the analysis folder used by this run.
    run_info : RunInfo
        The ``RunInfo`` returned by ``optimize_rigorously``.
    conv : object or None
        Convergence info returned by ``Decomposition.plot_convergence``;
        ``None`` if results never materialised within ``timeout``.
    best : Decomposition or None
        Best-result decomposition from ``load_best_rigorous_result``;
        ``None`` if no result.
    rgs : list[float] or None
        Component Rg values from ``best.get_rgs()``; ``None`` if no result.
    elapsed : float
        Wall-clock seconds for the ``optimize_rigorously`` call.
    completed : bool
        ``True`` iff ``conv`` and ``best`` are both populated.
    """

    __slots__ = ('label', 'in_process', 'analysis_folder', 'run_info',
                 'conv', 'best', 'rgs', 'elapsed', 'completed')

    def __init__(self, label, in_process, analysis_folder, run_info,
                 conv, best, rgs, elapsed, completed):
        self.label = label
        self.in_process = in_process
        self.analysis_folder = analysis_folder
        self.run_info = run_info
        self.conv = conv
        self.best = best
        self.rgs = rgs
        self.elapsed = elapsed
        self.completed = completed

    @property
    def best_fv(self):
        return None if self.conv is None else self.conv.best_fv

    @property
    def best_sv(self):
        return None if self.conv is None else self.conv.best_sv


class ComparisonResult:
    """Result of running ``optimize_rigorously`` along multiple paths.

    Returned by :func:`compare_optimization_paths`.

    Attributes
    ----------
    results : list[PathResult]
        One entry per path, in the order requested.
    niter : int
        ``niter`` value used for both runs.
    method : str
        Solver method used for both runs.
    rgcurve : object
        Rg curve passed to the runs (kept for ``plot_components``).
    """

    def __init__(self, results, niter, method, rgcurve):
        self.results = list(results)
        self.niter = niter
        self.method = method
        self.rgcurve = rgcurve

    def by_label(self, label):
        for r in self.results:
            if r.label == label:
                return r
        raise KeyError(
            "No result for label %r; have %s"
            % (label, [r.label for r in self.results])
        )

    def live_status(self, label=None):
        """Return :meth:`RunInfo.live_status` snapshots for the comparison.

        Convenience wrapper so callers don't have to spell out
        ``result.by_label('subprocess').run_info.live_status()``.

        Parameters
        ----------
        label : str, optional
            If given, return the single dict for that path (e.g.
            ``'subprocess'`` or ``'in_process'``).  If ``None`` (default),
            return ``{label: status_dict, ...}`` for every path that has
            a ``run_info`` available.

        Returns
        -------
        dict
            Either a single ``live_status`` dict (when ``label`` is given)
            or a mapping of ``label → live_status dict``.

        Examples
        --------
        ::

            result = compare_optimization_paths(decomp, rgcurve, niter=20)
            result.live_status()                      # both paths
            result.live_status('subprocess')          # one path
            aicKernelEval(expression="result.live_status()")
        """
        if label is not None:
            r = self.by_label(label)
            if r.run_info is None:
                return None
            return r.run_info.live_status()
        out = {}
        for r in self.results:
            if r.run_info is None:
                out[r.label] = None
            else:
                out[r.label] = r.run_info.live_status()
        return out

    def summary_table(self, file=None):
        """Print a side-by-side summary table.

        The format matches the hand-rolled table in
        ``13h_split_architecture_validation`` cell ``[8]`` so existing
        readers see the same shape.

        Parameters
        ----------
        file : file-like, optional
            Destination for the printed table; defaults to ``sys.stdout``.
        """
        if not self.results:
            print("No results to compare.", file=file)
            return

        labels = [r.label for r in self.results]
        col_w = max(14, max(len(lbl) for lbl in labels) + 2)

        # Header
        header = f"{'metric':<14}" + ''.join(f"{lbl:>{col_w}}" for lbl in labels)
        if len(self.results) == 2:
            header += f"{'delta':>14}"
        print(header, file=file)
        print('-' * len(header), file=file)

        def _row(name, getter, fmt, delta_fmt='+14.4f'):
            vals = [getter(r) for r in self.results]
            cells = ''
            for v in vals:
                cells += (f"{v:>{col_w}{fmt}}" if v is not None
                          else f"{'n/a':>{col_w}}")
            if len(vals) == 2 and all(v is not None for v in vals):
                cells += f"{vals[1] - vals[0]:{delta_fmt}}"
            print(f"{name:<14}" + cells, file=file)

        _row('best_fv', lambda r: r.best_fv, '.4f')
        _row('best_sv', lambda r: r.best_sv, '.2f', delta_fmt='+14.2f')

        # Rg rows
        n_comp = max((len(r.rgs) if r.rgs is not None else 0)
                     for r in self.results)
        for i in range(n_comp):
            def _get_rg(r, i=i):
                if r.rgs is None or i >= len(r.rgs):
                    return None
                v = r.rgs[i]
                if v is None:
                    return None
                v = float(v)
                if v != v:        # NaN
                    return None
                return v
            _row(f'Rg[{i+1}]', _get_rg, '.2f', delta_fmt='+14.2f')

        _row('wall (s)', lambda r: r.elapsed, '.1f', delta_fmt='+14.1f')

        if len(self.results) == 2:
            a, b = self.results
            if a.best_fv is not None and b.best_fv is not None:
                print(file=file)
                print(f"|delta best_fv| = "
                      f"{abs(b.best_fv - a.best_fv):.4e}", file=file)
                print(f"|delta best_sv| = "
                      f"{abs(b.best_sv - a.best_sv):.4e}", file=file)

    def plot_convergence(self, figsize=None):
        """Side-by-side convergence plot, one panel per path."""
        import matplotlib.pyplot as plt

        completed = [r for r in self.results if r.completed]
        if not completed:
            print("No completed runs to plot.")
            return None

        n = len(self.results)
        fig, axes = plt.subplots(1, n,
                                 figsize=figsize or (6 * n, 4),
                                 sharey=True)
        if n == 1:
            axes = [axes]

        for ax, r in zip(axes, self.results):
            if not r.completed:
                ax.set_title(f"{r.label} — no result")
                ax.axis('off')
                continue
            fvs = getattr(r.conv, 'fv_history', None)
            if fvs is not None and len(fvs) > 0:
                best_so_far = np.minimum.accumulate(np.asarray(fvs, dtype=float))
                ax.plot(best_so_far, lw=1.5)
                ax.set_xlabel("evaluation")
            else:
                ax.axhline(r.best_fv, color='C1', lw=1.5)
                ax.set_xlabel("(no fv_history)")
            ax.set_title(
                f"{r.label}  best_fv={r.best_fv:.4f}  "
                f"sv={r.best_sv:.2f}  ({r.elapsed:.1f}s)"
            )
            ax.grid(True, alpha=0.3)

        axes[0].set_ylabel("best fv so far")
        fig.suptitle(
            f"compare_optimization_paths — method={self.method}, "
            f"niter={self.niter}"
        )
        fig.tight_layout()
        plt.show()
        return fig

    def plot_components(self):
        """Plot best-result components for each completed path."""
        for r in self.results:
            if not r.completed:
                continue
            r.best.plot_components(
                rgcurve=self.rgcurve,
                title=(f"{r.label} — rigorous "
                       f"(fv={r.best_fv:.4f}, sv={r.best_sv:.2f})"),
            )

    def assert_parity(self, fv_rtol=1e-2, sv_atol=1.0, rg_atol=0.5):
        """Assert that all path results agree within tolerances.

        Intended for the validation workflow: a passing assertion means
        the in-process path reproduces the subprocess path's result on
        the given problem (within stochastic tolerance).

        Parameters
        ----------
        fv_rtol : float, optional
            Relative tolerance on ``best_fv`` between paths. Default ``1e-2``.
        sv_atol : float, optional
            Absolute tolerance on ``best_sv``. Default ``1.0`` SV point.
        rg_atol : float, optional
            Absolute tolerance on per-component Rg in ångström.
            Default ``0.5`` Å.

        Raises
        ------
        AssertionError
            If any path is incomplete or any pairwise comparison exceeds
            tolerance.
        """
        completed = [r for r in self.results if r.completed]
        if len(completed) < 2:
            raise AssertionError(
                "assert_parity needs >= 2 completed runs; got %d"
                % len(completed)
            )

        ref = completed[0]
        for other in completed[1:]:
            # best_fv
            if ref.best_fv == 0:
                if abs(other.best_fv) > fv_rtol:
                    raise AssertionError(
                        "%s vs %s: best_fv differs (%g vs %g)"
                        % (ref.label, other.label, ref.best_fv, other.best_fv)
                    )
            else:
                rel = abs(other.best_fv - ref.best_fv) / abs(ref.best_fv)
                if rel > fv_rtol:
                    raise AssertionError(
                        "%s vs %s: best_fv relative diff %.3g > %.3g "
                        "(%.4f vs %.4f)"
                        % (ref.label, other.label, rel, fv_rtol,
                           ref.best_fv, other.best_fv)
                    )
            # best_sv
            if abs(other.best_sv - ref.best_sv) > sv_atol:
                raise AssertionError(
                    "%s vs %s: best_sv diff %.3g > %.3g (%.2f vs %.2f)"
                    % (ref.label, other.label,
                       abs(other.best_sv - ref.best_sv), sv_atol,
                       ref.best_sv, other.best_sv)
                )
            # Rg per-component
            n = min(len(ref.rgs or []), len(other.rgs or []))
            for i in range(n):
                a = ref.rgs[i]
                b = other.rgs[i]
                if a is None or b is None:
                    continue
                a = float(a); b = float(b)
                if a != a or b != b:
                    continue
                if abs(b - a) > rg_atol:
                    raise AssertionError(
                        "%s vs %s: Rg[%d] diff %.2f Å > %.2f Å "
                        "(%.2f vs %.2f)"
                        % (ref.label, other.label, i + 1,
                           abs(b - a), rg_atol, a, b)
                    )


def _summarize_path(label, in_process, run_info, decomposition, rgcurve,
                    elapsed, timeout):
    """Wait for results and build a :class:`PathResult`.

    Mirrors the ``_summarize`` helper used in
    ``13h_split_architecture_validation`` but lives in the API so users
    don't have to redefine it per notebook.
    """
    from molass.LowRank.Decomposition import Decomposition

    analysis_folder = run_info.analysis_folder

    if not Decomposition.wait_for_rigorous_results(analysis_folder, timeout=timeout):
        return PathResult(
            label=label, in_process=in_process,
            analysis_folder=analysis_folder, run_info=run_info,
            conv=None, best=None, rgs=None,
            elapsed=elapsed, completed=False,
        )

    conv = Decomposition.plot_convergence(
        analysis_folder, title=f"{label} convergence"
    )
    best = decomposition.load_best_rigorous_result(
        analysis_folder, rgcurve=rgcurve
    )
    rgs = best.get_rgs()
    return PathResult(
        label=label, in_process=in_process,
        analysis_folder=analysis_folder, run_info=run_info,
        conv=conv, best=best, rgs=rgs,
        elapsed=elapsed, completed=True,
    )


def compare_optimization_paths(decomposition, rgcurve, *,
                               method='NS', niter=20,
                               paths=('subprocess', 'in_process'),
                               trimmed_ssd=None,
                               analysis_folder_prefix=None,
                               timeout=600,
                               clear_jobs=True,
                               frozen_components=None,
                               function_code=None,
                               monitor=False,
                               debug=False,
                               **kwargs):
    """Run ``optimize_rigorously`` along each requested path and compare.

    Single-cell entry point for split-architecture validation.  Each path
    runs the same optimization problem, results are gathered into a
    :class:`ComparisonResult`, and the summary table / convergence plot
    / parity assertion are available as one-line method calls.

    Parameters
    ----------
    decomposition : Decomposition
        Initial decomposition (from ``corrected.quick_decomposition``).
    rgcurve : Curve
        Rg component curve.
    method : str, optional
        Solver method passed to ``optimize_rigorously``. Default ``'NS'``.
    niter : int, optional
        Iteration count for both runs. Default ``20``.
    paths : sequence of str, optional
        Paths to run. Each entry must be one of ``'subprocess'``,
        ``'in_process'`` (or aliases ``'sub'`` / ``'inp'``).
        Default ``('subprocess', 'in_process')``.
    trimmed_ssd : SecSaxsData, optional
        Trimmed SSD (passed through to ``optimize_rigorously``).
    analysis_folder_prefix : str, optional
        If given, each path's analysis folder is
        ``f"{analysis_folder_prefix}_{label}_{HHMMSS}"``. If ``None``,
        a temp-style ``analysis_split_{label}_{HHMMSS}`` is used in the
        current working directory.
    timeout : float, optional
        Per-path timeout passed to ``wait_for_rigorous_results``.
        Default ``600`` s.
    monitor : bool, optional
        Forwarded to ``optimize_rigorously`` for the subprocess leg.
        Default ``False`` — the comparison does not need the live
        ``MplMonitor`` dashboard, and skipping it avoids the matplotlib /
        ipywidgets fragility that has crashed the kernel on accept events
        (Python 3.14 + degraded widget CDN).  Set ``True`` only if you
        also want the dashboard while the comparison runs.
    clear_jobs, frozen_components, function_code, debug, **kwargs :
        Passed through to ``optimize_rigorously``.

    Returns
    -------
    ComparisonResult
    """
    if not paths:
        raise ValueError("paths must be non-empty")

    tag = time.strftime("%H%M%S")
    results = []

    for label in paths:
        in_process = _resolve_path(label)
        # Normalise the user's label to the canonical form for display.
        canonical = 'in_process' if in_process else 'subprocess'

        if analysis_folder_prefix is None:
            folder = f"analysis_split_{canonical}_{tag}"
        else:
            folder = f"{analysis_folder_prefix}_{canonical}_{tag}"
        folder = os.path.abspath(folder)

        print(f"=== {canonical} path ===")
        t0 = time.time()
        run_info = decomposition.optimize_rigorously(
            rgcurve=rgcurve,
            analysis_folder=folder,
            trimmed_ssd=trimmed_ssd,
            method=method,
            niter=niter,
            clear_jobs=clear_jobs,
            in_process=in_process,
            monitor=monitor,
            frozen_components=frozen_components,
            function_code=function_code,
            debug=debug,
            **kwargs,
        )
        elapsed = time.time() - t0
        print(f"optimize_rigorously ({canonical}) done in {elapsed:.1f}s")

        path_result = _summarize_path(
            label=canonical, in_process=in_process,
            run_info=run_info, decomposition=decomposition,
            rgcurve=rgcurve, elapsed=elapsed, timeout=timeout,
        )
        results.append(path_result)

    return ComparisonResult(
        results=results, niter=niter, method=method, rgcurve=rgcurve,
    )
