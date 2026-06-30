"""
molass.Rigorous.InitialScore

Evaluate the rigorous objective function **once** at initial parameters,
returning SV, score breakdown, and a PeakEditor-like visual — without
running full BH/NS optimization.

Usage
-----
::

    result = decomp.score_initial(trimmed_ssd=trimmed)
    print(f"SV = {result.sv:.2f}")
    result.plot(title="Auto EGH initial score")
    result.print_summary()
    for d in result.diagnose():
        print(f"[{d.status}] {d.score}: {d.reason}")

Copyright (c) 2026, SAXS Team, KEK-PF
"""
from __future__ import annotations

import io
import os
import warnings
from contextlib import redirect_stdout, redirect_stderr, ExitStack
from importlib import reload


class InitialScoreResult:
    """Result of a single rigorous objective evaluation at initial parameters.

    Produced by :meth:`~molass.LowRank.Decomposition.Decomposition.score_initial`.

    Attributes
    ----------
    fv : float
        Raw objective value (lower is better).
    sv : float
        Score value on the 0–100 scale (higher is better).
    breakdown : dict
        ``{'fv': float, 'scores': {name: value, ...}}`` — same structure
        as :meth:`~molass.Rigorous.RunInfo.RunInfo.get_score_breakdown`.
    optimizer : legacy optimizer object
        Fully constructed and prepared at ``init_params``.
    init_params : ndarray
        Physical parameter vector used for the evaluation.
    """

    def __init__(self, fv, sv, breakdown, optimizer, init_params):
        self.fv = fv
        self.sv = sv
        self.breakdown = breakdown
        self.optimizer = optimizer
        self.init_params = init_params

    # ------------------------------------------------------------------
    # Visual
    # ------------------------------------------------------------------

    def plot(self, title=None):
        """Produce the 3-panel UV/XR/scores figure (like PeakEditor's final plot).

        The three panels show:

        * Left: UV elution decomposition (data vs modelled components)
        * Centre: XR elution decomposition (data vs modelled components)
        * Right: objective function score components (bar chart)

        Parameters
        ----------
        title : str, optional
            Figure suptitle.  Defaults to ``"Initial score — SV=<value>"``.

        Returns
        -------
        matplotlib.figure.Figure
        """
        import matplotlib.pyplot as plt
        from molass_legacy.Optimizer.JobStatePlot import plot_objective_func

        fig, axes = plt.subplots(ncols=3, figsize=(18, 4.5))
        ax1, ax2, ax3 = axes
        axt = ax2.twinx()
        axt.grid(False)
        axis_info = (fig, (ax1, ax2, ax3, axt))

        _title = title or f"Initial score — SV={self.sv:.2f}"
        fig.suptitle(_title, fontsize=13)

        # plot_objective_func evaluates objective_func(params, plot=True) internally
        self.optimizer.objective_func(self.init_params, plot=True, axis_info=axis_info)
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # Score analysis
    # ------------------------------------------------------------------

    def diagnose(self, breakdown=None):
        """Map score values to physical interpretations.

        Delegates to the same rules as
        :meth:`~molass.Rigorous.RunInfo.RunInfo.diagnose`.

        Parameters
        ----------
        breakdown : dict, optional
            If None (default), uses ``self.breakdown``.

        Returns
        -------
        list of Diagnosis namedtuples
            Each has ``score``, ``status``, ``reason``, ``suggestion``.
        """
        from molass.Rigorous.RunInfo import RunInfo
        # Minimal proxy: diagnose() only uses self when breakdown is None
        # (to call get_score_breakdown() from disk).  By passing breakdown
        # directly we avoid any disk access.
        _proxy = object.__new__(RunInfo)
        if breakdown is None:
            breakdown = self.breakdown
        return RunInfo.diagnose(_proxy, breakdown=breakdown)

    def print_summary(self):
        """Print SV, breakdown table, and diagnosis to stdout."""
        print(f"SV = {self.sv:.2f}  (fv = {self.fv:.4f})")
        print("\nScore breakdown:")
        for k, v in self.breakdown['scores'].items():
            print(f"  {k:35s}: {v:+.4f}")
        print("\nDiagnosis:")
        for d in self.diagnose():
            print(f"  [{d.status:7s}] {d.score:35s}: {d.reason}")

    def __repr__(self):
        return f"InitialScoreResult(sv={self.sv:.2f}, fv={self.fv:.4f})"


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------

def make_initial_score_impl(decomposition, trimmed_ssd=None,
                             analysis_folder=None, function_code=None,
                             debug=False):
    """Set up the rigorous optimizer, evaluate the objective once, return InitialScoreResult.

    This mirrors the setup phase of
    :func:`~molass.Rigorous.RigorousImplement.make_rigorous_decomposition_impl`
    but stops immediately after ``optimizer.prepare_for_optimization(init_params)``
    and evaluates the objective function once instead of running BH/NS.

    A temporary folder is used when ``analysis_folder`` is None (cleaned up
    after the call).

    Parameters
    ----------
    decomposition : Decomposition
    trimmed_ssd : SecSaxsData, optional
        Trimmed (uncorrected) SSD.  Recommended (Pattern B).
    analysis_folder : str, optional
        Where to write optimizer setup files.  Defaults to a temp folder.
    function_code : str, optional
        Override auto-detected function code.
    debug : bool, optional
    """
    import numpy as np
    import tempfile, shutil

    # Use a temp dir when no folder is provided — everything is in-process,
    # so the disk writes (rg-curve, .npy exports) are just a setup artefact
    # that we clean up immediately.
    _tmp_dir = None
    if analysis_folder is None:
        _tmp_dir = tempfile.mkdtemp(prefix="molass_score_initial_")
        analysis_folder = _tmp_dir

    try:
        return _make_initial_score_core(
            decomposition, trimmed_ssd=trimmed_ssd,
            analysis_folder=analysis_folder,
            function_code=function_code, debug=debug,
        )
    finally:
        if _tmp_dir is not None:
            try:
                shutil.rmtree(_tmp_dir, ignore_errors=True)
            except Exception:
                pass


def _make_initial_score_core(decomposition, trimmed_ssd, analysis_folder,
                              function_code, debug):
    """Inner implementation (analysis_folder is always provided)."""
    import numpy as np
    from molass.Rigorous.RigorousImplement import _apply_anomaly_interpolation

    import molass.Rigorous.LegacyBridgeUtils
    reload(molass.Rigorous.LegacyBridgeUtils)
    import molass.Rigorous.FunctionCodeUtils
    reload(molass.Rigorous.FunctionCodeUtils)
    from molass.Rigorous.LegacyBridgeUtils import (
        prepare_rigorous_folders,
        make_dsets_from_decomposition,
        make_basecurves_from_decomposition,
        construct_legacy_optimizer,
    )

    # Pattern A warning — same as in make_rigorous_decomposition_impl
    if trimmed_ssd is None and getattr(decomposition.ssd, 'corrected', False):
        warnings.warn(
            "score_initial() is running on corrected data (Pattern A). "
            "Pass trimmed_ssd=<your trimmed SSD> (Pattern B) for a more accurate baseline evaluation.",
            UserWarning, stacklevel=4,
        )

    # Apply anomaly interpolation if present
    if trimmed_ssd is not None:
        trimmed_ssd = _apply_anomaly_interpolation(
            trimmed_ssd, corrected_ssd=decomposition.ssd
        )

    # Suppress verbose legacy output
    _stack = ExitStack()
    if not debug:
        _stack.enter_context(redirect_stdout(io.StringIO()))
        _stack.enter_context(redirect_stderr(io.StringIO()))
        _wctx = warnings.catch_warnings()
        _stack.enter_context(_wctx)
        warnings.simplefilter("ignore")

    # Capture original in_folder before prepare_rigorous_folders overwrites it
    from molass_legacy.SerialAnalyzer.DataUtils import get_in_folder as _get_in_folder_raw
    _original_in_folder = _get_in_folder_raw()

    with _stack:
        dsets, basecurves, baseparams, exported = prepare_rigorous_folders(
            decomposition, decomposition.get_rg_curve(),
            analysis_folder=analysis_folder,
            data_ssd=trimmed_ssd, debug=debug,
        )

        data_ssd = trimmed_ssd if trimmed_ssd is not None else decomposition.ssd

        from molass_legacy.SecSaxs.DataTreatment import DataTreatment
        treat = DataTreatment(
            route="v2", trimming=2, correction=1, unified_baseline_type=1
        )
        treat.save()

        if exported:
            from molass.Rigorous.RigorousImplement import _set_identity_restrict_lists
            _set_identity_restrict_lists(data_ssd)
        else:
            decomposition.ssd.trimming.update_legacy_settings()

        spectral_vectors = data_ssd.get_spectral_vectors()
        model = decomposition.xr_ccurves[0].model
        num_components = decomposition.num_components

        if function_code is None:
            from molass.Rigorous.FunctionCodeUtils import detect_function_code
            function_code = detect_function_code(decomposition)

        optimizer = construct_legacy_optimizer(
            dsets, basecurves, spectral_vectors,
            num_components=num_components, model=model,
            method='BH',  # method only affects optimizer setup, not objective_func
            function_code=function_code, debug=debug,
        )
        optimizer.set_xr_only(not data_ssd.has_uv())

        from molass_legacy.Optimizer.Scripting import set_optimizer_settings
        set_optimizer_settings(
            num_components=num_components, model=model, method='BH'
        )

        init_params = decomposition.make_rigorous_initparams(baseparams)
        optimizer.prepare_for_optimization(init_params)

    # Evaluate objective once (outside suppression so exceptions are visible)
    result_full = optimizer.objective_func(init_params, return_full=True)
    fv = float(result_full[0])
    score_array = result_full[1]
    names = optimizer.get_score_names()
    scores = {name: float(val) for name, val in zip(names, score_array)}
    breakdown = {'fv': fv, 'scores': scores}

    from molass.Rigorous.CurrentStateUtils import fv_to_sv
    sv = float(fv_to_sv(fv))

    return InitialScoreResult(
        fv=fv, sv=sv, breakdown=breakdown,
        optimizer=optimizer, init_params=init_params,
    )
