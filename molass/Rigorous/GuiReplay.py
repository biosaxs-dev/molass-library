"""
    molass.Rigorous.GuiReplay

    Reconstruct a legacy GUI optimizer run in-process for notebook introspection.

    This module bridges the gap between the opaque LEG-GUI subprocess path and
    the notebook API.  It reads the files produced by a completed GUI run
    (callback.txt, init_params.txt, optimizer.log, opt_settings.txt, ip_*.npy)
    and reconstructs the optimizer in the calling process so it can be:

    - queried for score_breakdown at any parameter vector
    - re-run with any solver for direct comparison
    - compared against LIB-IN results using compare_dsets()

    Alignment with the refactor architecture:
    - molass-library is the home for active computational code (ARCHITECTURE.md)
    - This module calls molass-legacy's DsetsDebug layer for raw reconstruction
    - Returns RunInfo so the result is consumable through the library's API
    - Serves the data-object consolidation track: makes the GUI's sd-based
      landscape directly inspectable, creating pressure to replace sd with ssd

    Usage example
    -------------
    from molass.Rigorous.GuiReplay import load_gui_scenario

    scenario = load_gui_scenario(r'C:\\PyTools\\reports\\analysis-005')
    print('fv_init from GUI callback:', scenario.fv_init)
    print('fv_init reproduced      :', scenario.eval_init())

    # Re-run in-process with BH for comparison
    run = scenario.run_inprocess(method='BH', niter=20)
    run.wait()
    bd = run.get_score_breakdown()

    Copyright (c) 2026, SAXS Team, KEK-PF
"""
from __future__ import annotations

import os
import re
import logging
import numpy as np
from collections import namedtuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public return type
# ---------------------------------------------------------------------------

class GuiScenario:
    """Reconstructed GUI optimizer scenario, ready for in-process introspection.

    Attributes
    ----------
    analysis_folder : str
    work_folder : str
        Path to the job folder (e.g. ``analysis_folder/optimized/jobs/000``).
    optimizer : legacy optimizer object
        Fully constructed and prepared (``prepare_for_optimization`` already
        called with ``init_params``).
    init_params : ndarray
        Physical parameter vector from ``init_params.txt``.
    fv_init : float
        Objective value at ``init_params`` as recorded in ``callback.txt``.
    n_components : int
    class_code : str
    """

    def __init__(self, analysis_folder, work_folder, optimizer, init_params,
                 fv_init, n_components, class_code):
        self.analysis_folder = analysis_folder
        self.work_folder = work_folder
        self.optimizer = optimizer
        self.init_params = init_params
        self.fv_init = fv_init
        self.n_components = n_components
        self.class_code = class_code

    def eval_init(self):
        """Evaluate the objective at init_params in-process.

        Returns the reproduced fv_init.  Compare with self.fv_init (from
        callback.txt) to verify the reconstruction is faithful.
        """
        return float(self.optimizer.objective_func(self.init_params))

    def get_score_breakdown(self, params=None):
        """Return score breakdown at init_params (or any given params).

        Returns
        -------
        dict  {'fv': float, 'scores': {name: value}}
            Same structure as RunInfo.get_score_breakdown().
        """
        if params is None:
            params = self.init_params
        result = self.optimizer.objective_func(params, return_full=True)
        fv = float(result[0])
        score_array = result[1]
        names = self.optimizer.get_score_names()
        scores = {name: float(val) for name, val in zip(names, score_array)}
        return {'fv': fv, 'scores': scores}

    def run_inprocess(self, method='BH', niter=20, seed=1234,
                      analysis_folder=None, **solver_kwargs):
        """Re-run the optimizer in-process with any solver.

        This lets you run BH or DE on exactly the GUI's data and compare
        the result against the original LEG-GUI outcome.

        Parameters
        ----------
        method : str
            Solver name ('BH', 'DE', 'CMA', etc.).
        niter : int
            Budget.
        seed : int
        analysis_folder : str or None
            Where to write the new run's output.  Defaults to a temp folder
            inside work_folder.
        **solver_kwargs
            Forwarded to optimize_rigorously (e.g. de_variant, de_pop_size).

        Returns
        -------
        RunInfo
        """
        if analysis_folder is None:
            analysis_folder = os.path.join(
                self.work_folder, 'gui_replay_%s' % method.lower())

        # We need a Decomposition-like object to call optimize_rigorously.
        # Build a minimal one from the optimizer's dsets.
        from molass.Rigorous.RunInfo import RunInfo
        from molass_legacy.Optimizer.InProcessRunner import run_optimizer_in_process

        optimizer = self.optimizer
        init_params = self.init_params

        # Re-prepare with the stored init_params (already done in load_gui_scenario,
        # but re-prepare is idempotent and safe to call again before a new run).
        optimizer.prepare_for_optimization(init_params)

        from molass_legacy.Optimizer.Scripting import set_optimizer_settings
        set_optimizer_settings(method=method, **solver_kwargs)

        run_info = RunInfo(
            ssd=None,
            optimizer=optimizer,
            dsets=None,
            init_params=init_params,
            monitor=False,
        )

        import threading
        stop_event = threading.Event()
        optimizer._stop_event = stop_event

        def _run():
            import os as _os
            prev = _os.getcwd()
            _os.chdir(self.work_folder)
            try:
                run_optimizer_in_process(
                    optimizer, init_params, niter=niter, seed=seed,
                    method=method.lower(),
                    work_folder=self.work_folder,
                    run_info=run_info,
                )
            finally:
                _os.chdir(prev)

        t = threading.Thread(target=_run, daemon=True, name='gui-replay')
        t.start()
        run_info._async_thread = t
        return run_info


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def load_gui_scenario(analysis_folder, job='000'):
    """Reconstruct a completed GUI run as a GuiScenario for notebook introspection.

    Reads all files produced by the LEG-GUI subprocess (init_params.txt,
    optimizer.log, opt_settings.txt, ip_*.npy) and reconstructs the optimizer
    in the calling process with the same data the subprocess used.

    Parameters
    ----------
    analysis_folder : str
        Path to the analysis folder (e.g. ``r'C:\\PyTools\\reports\\analysis-005'``).
    job : str
        Job subfolder name, default ``'000'``.

    Returns
    -------
    GuiScenario

    Raises
    ------
    FileNotFoundError
        If required files are missing.
    """
    from importlib import reload

    analysis_folder = os.path.abspath(analysis_folder)
    work_folder = os.path.join(analysis_folder, 'optimized', 'jobs', job)
    optimizer_folder = os.path.join(analysis_folder, 'optimized')

    if not os.path.isdir(work_folder):
        raise FileNotFoundError(
            f"Job folder not found: {work_folder}"
        )

    # ── 1. Parse n_components and class_code from optimizer.log ──────────────
    n_components, class_code = _parse_optimizer_log(work_folder)
    logger.info("Parsed from optimizer.log: n_components=%d, class_code=%s",
                n_components, class_code)

    # ── 2. Read init_params ──────────────────────────────────────────────────
    init_params_file = os.path.join(work_folder, 'init_params.txt')
    if not os.path.exists(init_params_file):
        raise FileNotFoundError(f"init_params.txt not found: {init_params_file}")
    init_params = np.loadtxt(init_params_file)

    # ── 3. Read fv_init from callback.txt (first recorded fv) ────────────────
    cb_file = os.path.join(work_folder, 'callback.txt')
    fv_init = _read_fv_init(cb_file)

    # ── 4. Set SerialSettings so reconstruction reads the right folders ──────
    from molass_legacy._MOLASS.SerialSettings import set_setting
    set_setting('analysis_folder', analysis_folder)
    set_setting('optimizer_folder', optimizer_folder)

    # Restore opt_settings.txt into SerialSettings
    opt_settings_file = os.path.join(optimizer_folder, 'opt_settings.txt')
    if os.path.exists(opt_settings_file):
        from molass_legacy.Optimizer.OptimizerSettings import OptimizerSettings
        settings = OptimizerSettings()
        settings.load(path=opt_settings_file)
        logger.info("Restored opt_settings from %s", opt_settings_file)

    # ── 5. Reconstruct optimizer via DsetsDebug ───────────────────────────────
    import molass_legacy.Optimizer.DsetsDebug
    reload(molass_legacy.Optimizer.DsetsDebug)
    from molass_legacy.Optimizer.DsetsDebug import reconstruct_subprocess_optimizer

    optimizer = reconstruct_subprocess_optimizer(
        work_folder=work_folder,
        n_components=n_components,
        class_code=class_code,
    )

    # ── 6. Prepare optimizer with init_params ────────────────────────────────
    optimizer.prepare_for_optimization(init_params)

    logger.info("GuiScenario ready: fv_init=%.4f (callback), "
                "n_components=%d, class_code=%s",
                fv_init if fv_init is not None else float('nan'),
                n_components, class_code)

    return GuiScenario(
        analysis_folder=analysis_folder,
        work_folder=work_folder,
        optimizer=optimizer,
        init_params=init_params,
        fv_init=fv_init,
        n_components=n_components,
        class_code=class_code,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_optimizer_log(work_folder):
    """Parse n_components and class_code from optimizer.log."""
    log_file = os.path.join(work_folder, 'optimizer.log')
    if not os.path.exists(log_file):
        raise FileNotFoundError(
            f"optimizer.log not found in {work_folder}. "
            "Cannot determine n_components / class_code automatically. "
            "Pass them explicitly if needed."
        )
    text = open(log_file).read()

    # Match the sys.argv line: ['-c', 'G0346', ... '-n', '4', ...]
    m_cc = re.search(r"'-c',\s*'([^']+)'", text)
    m_nc = re.search(r"'-n',\s*'(\d+)'", text)

    if not m_cc:
        raise ValueError(
            "Could not parse class_code (-c) from optimizer.log. "
            f"Log excerpt:\n{text[:500]}"
        )
    if not m_nc:
        raise ValueError(
            "Could not parse n_components (-n) from optimizer.log. "
            f"Log excerpt:\n{text[:500]}"
        )

    return int(m_nc.group(1)), m_cc.group(1)


def _read_fv_init(cb_file):
    """Return the first recorded fv from callback.txt (= fv at init_params)."""
    if not os.path.exists(cb_file):
        return None
    text = open(cb_file).read()
    m = re.search(r'(?m)^f=([-\d.eE+]+)', text)
    return float(m.group(1)) if m else None
