"""
Rigorous.CurrentStateUtils.py
"""
import os
import numpy as np
from collections import namedtuple
from molass_legacy._MOLASS.SerialSettings import get_setting
from molass_legacy.Optimizer.Scripting import get_params
from molass.LowRank.Decomposition import Decomposition
from molass.SEC.Models.UvComponentCurve import UvComponentCurve
from molass.Mapping.Mapping import Mapping

JobInfo = namedtuple('JobInfo', ['id', 'iterations', 'best_fv', 'timestamp'])
JobConvergence = namedtuple('JobConvergence', ['id', 'evals', 'fvs', 'best_fv', 'best_sv', 'timestamps'])
ConvergenceInfo = namedtuple('ConvergenceInfo', [
    'jobs', 'best_fv', 'best_sv', 'best_job_id', 'spread', 'trend', 'n_jobs',
])

JobInfo.__doc__ = """Metadata for a single rigorous optimization job.

Attributes: id, iterations, best_fv, timestamp.
"""

JobConvergence.__doc__ = """Per-job convergence detail with full fv trajectory.

Attributes: id, evals (list of eval counts), fvs (list of fv values),
best_fv, best_sv, timestamps (list of datetimes).
"""

ConvergenceInfo.__doc__ = """Summary of convergence across all jobs.

Attributes: jobs (list of JobConvergence), best_fv, best_sv, best_job_id,
spread, trend ('improving'/'worsening'/'stable'), n_jobs.
"""


def fv_to_sv(fv):
    """Convert objective function value (fv) to Score Value (SV, 0-100 scale).

    The raw optimizer objective fv is negative and nonlinear, making it hard
    to interpret. SV maps it to a human-readable 0-100 quality scale via:

        SV = -200 / (1 + exp(-1.5 * fv)) + 100

    Quality thresholds:
        SV >= 80 : Good (green in plot_convergence)
        SV 60-80 : Fair (orange)
        SV <  60 : Poor (red)

    Reference points:
        fv = -3  -> SV ~= 98
        fv = -1  -> SV ~= 64
        fv =  0  -> SV =   0

    Can also be applied to individual score values (not just the total fv)
    to identify which objectives are bottlenecks.

    Parameters
    ----------
    fv : float or array-like
        Objective function value(s).

    Returns
    -------
    float or ndarray
        Score Value(s) on 0-100 scale.
    """
    import numpy as np
    fv = np.asarray(fv, dtype=float)
    return -200.0 / (1.0 + np.exp(-1.5 * fv)) + 100.0

def construct_decomposition_from_results(run_info, **kwargs):      
    optimizer_folder = get_setting('optimizer_folder')
    wait_for_first_results = kwargs.get('wait_for_first_results', False)
    if wait_for_first_results:
        print(f"Waiting for first results in optimizer folder: {optimizer_folder}")
        import time
        while True:
            jobs_folder = os.path.join(optimizer_folder, "jobs")
            if os.path.exists(jobs_folder):
                jobids = [d for d in os.listdir(jobs_folder) if os.path.isdir(os.path.join(jobs_folder, d))]
                if len(jobids) > 0:
                    job_result_folder = os.path.join(optimizer_folder, "jobs", jobids[-1])
                    result_file = os.path.join(job_result_folder, "callback.txt")
                    if os.path.exists(result_file):
                        try:
                            params = get_params(job_result_folder)
                            break
                        except Exception:
                            pass
            time.sleep(1)
 
    print(f"Loading current decomposition from optimizer folder: {optimizer_folder}")
    jobid = kwargs.get('jobid', None)
    if jobid is None:
        jobs_folder = os.path.join(optimizer_folder, "jobs")
        jobids = [d for d in os.listdir(jobs_folder) if os.path.isdir(os.path.join(jobs_folder, d))]
        jobids.sort()
        jobid = jobids[-1]
    
    job_result_folder = os.path.join(optimizer_folder, "jobs", jobid)
    print(f"Using job id: {jobid}, folder: {job_result_folder}")

    ssd = run_info.ssd
    xr_icurve = ssd.xr.get_icurve()
    if ssd.has_uv():
        uv_icurve = ssd.uv.get_icurve()
    else:
        uv_icurve = None

    params = get_params(job_result_folder)
    optimizer = run_info.optimizer
    separated_params = optimizer.split_params_simple(params)

    # xr_ccurves
    from importlib import reload
    import molass.Rigorous.ComponentUtils
    reload(molass.Rigorous.ComponentUtils)
    from .ComponentUtils import get_xr_ccurves
    xr_ccurves = get_xr_ccurves(optimizer, xr_icurve, separated_params)

    # mapping
    a, b = separated_params[3]
    mapping = Mapping(a, b)

    # uv_ccurves
    uv_params = separated_params[4]
    uv_ccurves = []
    if uv_icurve is None:
        x = xr_icurve.x
    else:
        x = uv_icurve.x
    for xr_ccurve, scale in zip(xr_ccurves, uv_params):
        xr_h = xr_ccurve.get_scale_param()
        uv_ccurves.append(UvComponentCurve(x, mapping, xr_ccurve, scale/xr_h))
    return Decomposition(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs)


def load_rigorous_result(decomp, analysis_folder, jobid=None, rgcurve=None, debug=False):
    """Load a rigorous optimization result from disk without launching a subprocess.

    This is the static result viewer: it reads the saved parameter vector from
    a completed job's ``callback.txt`` and reconstructs the ``Decomposition``
    using a lightweight (``for_split_only``) optimizer that only knows how to
    split parameters.

    Parameters
    ----------
    decomp : Decomposition
        The initial (quick) decomposition that was used as the starting point
        for rigorous optimization.  Provides ``ssd``, ``num_components``,
        model type, and baseline information.
    analysis_folder : str
        Path to the analysis folder used during optimization (same value
        passed to ``optimize_rigorously(analysis_folder=...)``).  
    jobid : str, optional
        Specific job id to load (subfolder name under ``optimized/jobs/``).  
        If ``None``, loads the latest (last sorted) job.
    rgcurve : RgCurve, optional
        Pre-computed Rg curve.  When provided, skips the expensive per-frame
        Guinier fitting that ``ssd.xr.compute_rgcurve()`` would perform.
    debug : bool, optional
        If True, reload modules from disk.

    Returns
    -------
    Decomposition
        A new Decomposition built from the optimized parameters.

    Examples
    --------
    After re-running cells 1-4 to restore ``corrected``, ``decomp``,
    ``rgcurve``::

        from molass.Rigorous.CurrentStateUtils import load_rigorous_result

        result = load_rigorous_result(decomp, "temp_analysis_scaffolded")
        result.plot_components(rgcurve=rgcurve)
    """
    from molass_legacy._MOLASS.SerialSettings import set_setting

    analysis_folder = os.path.abspath(analysis_folder)
    optimizer_folder = os.path.join(analysis_folder, "optimized")
    jobs_folder = os.path.join(optimizer_folder, "jobs")

    # Set legacy settings so other code can find the folders
    set_setting('analysis_folder', analysis_folder)
    set_setting('optimizer_folder', optimizer_folder)

    # Resolve job id
    if jobid is None:
        jobids = sorted(d for d in os.listdir(jobs_folder)
                        if os.path.isdir(os.path.join(jobs_folder, d)))
        if not jobids:
            raise FileNotFoundError(f"No job folders found in {jobs_folder}")
        jobid = jobids[-1]

    job_result_folder = os.path.join(jobs_folder, jobid)
    print(f"Loading rigorous result from job: {jobid}")

    # Load optimized parameters
    params = get_params(job_result_folder, debug=debug)

    # Build lightweight optimizer — for parameter splitting only, no heavy state
    if debug:
        from importlib import reload
        import molass.Rigorous.LegacyBridgeUtils
        reload(molass.Rigorous.LegacyBridgeUtils)
        import molass.Rigorous.FunctionCodeUtils
        reload(molass.Rigorous.FunctionCodeUtils)
    from molass.Rigorous.LegacyBridgeUtils import (
        make_dsets_from_decomposition,
        make_basecurves_from_decomposition,
        construct_legacy_optimizer,
    )

    ssd = decomp.ssd
    rgcurve_for_dsets = rgcurve if rgcurve is not None else ssd.xr.compute_rgcurve()
    import io, warnings
    from contextlib import redirect_stdout, redirect_stderr
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
         warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dsets = make_dsets_from_decomposition(decomp, rgcurve_for_dsets, debug=debug)
        basecurves, _ = make_basecurves_from_decomposition(decomp, debug=debug)
    spectral_vectors = ssd.get_spectral_vectors()
    model = decomp.xr_ccurves[0].model

    # Auto-select G1200 (SDM-Gamma) when applicable.  See issue #89.
    from .FunctionCodeUtils import detect_function_code
    function_code = detect_function_code(decomp)

    optimizer = construct_legacy_optimizer(
        dsets, basecurves, spectral_vectors,
        num_components=decomp.num_components,
        model=model,
        function_code=function_code,
        for_split_only=True,
    )

    # Split parameters → component arrays
    separated_params = optimizer.split_params_simple(params)

    # Reconstruct XR component curves
    if debug:
        from importlib import reload
        import molass.Rigorous.ComponentUtils
        reload(molass.Rigorous.ComponentUtils)
    from .ComponentUtils import get_xr_ccurves
    xr_icurve = ssd.xr.get_icurve()
    xr_ccurves = get_xr_ccurves(optimizer, xr_icurve, separated_params)

    # Mapping and UV component curves
    a, b = separated_params[3]
    mapping = Mapping(a, b)
    uv_params = separated_params[4]

    if ssd.has_uv():
        uv_icurve = ssd.uv.get_icurve()
        x = uv_icurve.x
    else:
        uv_icurve = None
        x = xr_icurve.x

    uv_ccurves = []
    for xr_ccurve, scale in zip(xr_ccurves, uv_params):
        xr_h = xr_ccurve.get_scale_param()
        uv_ccurves.append(UvComponentCurve(x, mapping, xr_ccurve, scale / xr_h))

    # Preserve the optimizer's Rg values so that
    # compute_reconstructed_rgcurve() matches MplMonitor.
    optimizer_rgs = np.asarray(separated_params[2], dtype=float)

    return Decomposition(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves,
                         optimizer_rgs=optimizer_rgs)


def list_rigorous_jobs(analysis_folder):
    """List completed rigorous optimization jobs on disk.

    Scans the ``analysis_folder/optimized/jobs/`` directory and returns
    metadata for each job that has a ``callback.txt`` file.

    Parameters
    ----------
    analysis_folder : str
        The same ``analysis_folder`` passed to ``optimize_rigorously()``.

    Returns
    -------
    list of JobInfo
        Each entry is a ``JobInfo(id, iterations, best_fv, timestamp)``
        namedtuple.  The list is sorted by job id.

    Examples
    --------
    ::

        jobs = decomp.list_rigorous_jobs("temp_analysis_scaffolded")
        for job in jobs:
            print(f"Job {job.id}: {job.iterations} iters, best fv={job.best_fv:.4f}")
    """
    import numpy as np
    from molass_legacy.Optimizer.StateSequence import read_callback_txt_impl

    analysis_folder = os.path.abspath(analysis_folder)
    jobs_folder = os.path.join(analysis_folder, "optimized", "jobs")

    if not os.path.exists(jobs_folder):
        return []

    result = []
    for d in sorted(os.listdir(jobs_folder)):
        job_dir = os.path.join(jobs_folder, d)
        if not os.path.isdir(job_dir):
            continue
        cb_file = os.path.join(job_dir, "callback.txt")
        if not os.path.exists(cb_file):
            continue

        fv_list, _ = read_callback_txt_impl(cb_file)
        if not fv_list:
            continue

        fv_arr = np.array(fv_list, dtype=object)
        iterations = len(fv_arr)
        best_fv = float(min(row[1] for row in fv_list))
        # Last iteration's timestamp (column 3)
        timestamp = fv_list[-1][3]

        result.append(JobInfo(id=d, iterations=iterations,
                              best_fv=best_fv, timestamp=timestamp))
    return result


def has_rigorous_results(analysis_folder):
    """Check whether any rigorous optimization results are available.

    This is a lightweight filesystem check — it does not parse results.
    Use this to poll readiness before calling ``load_rigorous_result()``
    or ``list_rigorous_jobs()``.

    Parameters
    ----------
    analysis_folder : str
        The same ``analysis_folder`` passed to ``optimize_rigorously()``.

    Returns
    -------
    bool
        ``True`` if at least one job has written a ``callback.txt`` file.

    Examples
    --------
    ::

        if decomp.has_rigorous_results("temp_analysis"):
            result = decomp.load_rigorous_result("temp_analysis")
    """
    analysis_folder = os.path.abspath(analysis_folder)
    jobs_folder = os.path.join(analysis_folder, "optimized", "jobs")

    if not os.path.isdir(jobs_folder):
        return False

    for d in os.listdir(jobs_folder):
        job_dir = os.path.join(jobs_folder, d)
        if os.path.isdir(job_dir) and os.path.exists(os.path.join(job_dir, "callback.txt")):
            return True

    return False


def wait_for_rigorous_results(analysis_folder, timeout=600, poll_interval=5):
    """Block until rigorous optimization results become available.

    Polls the filesystem at regular intervals until at least one job
    has a parseable ``callback.txt`` file, or the timeout is reached.

    Note: this checks ``list_rigorous_jobs()`` (not just file existence)
    to avoid a race condition where the file is created but not yet written.

    Parameters
    ----------
    analysis_folder : str
        The same ``analysis_folder`` passed to ``optimize_rigorously()``.
    timeout : float, optional
        Maximum seconds to wait (default 600 = 10 minutes).
        Use ``0`` or ``None`` for no timeout.
    poll_interval : float, optional
        Seconds between filesystem checks (default 5).

    Returns
    -------
    bool
        ``True`` if results appeared before timeout, ``False`` if timed out.

    Examples
    --------
    ::

        decomp.optimize_rigorously(analysis_folder="temp", ...)
        if Decomposition.wait_for_rigorous_results("temp"):
            result = decomp.load_rigorous_result("temp")
        else:
            print("Timed out waiting for results.")
    """
    import time

    elapsed = 0.0
    while not list_rigorous_jobs(analysis_folder):
        if timeout and elapsed >= timeout:
            return False
        time.sleep(poll_interval)
        elapsed += poll_interval

    return True


def parse_sv_history(analysis_folder):
    """Parse all ``callback.txt`` files and return the SV best-so-far trajectory.

    This is the pure data-extraction layer shared by :func:`check_progress`
    and :attr:`RunInfo.sv_history`.  No printing, no file writes.

    Parameters
    ----------
    analysis_folder : str
        Root folder for optimizer output (contains ``optimized/jobs/``).

    Returns
    -------
    list of float
        ``sv_best_so_far``: one SV value per accepted evaluation, accumulated
        as the running minimum.  Empty list if no evaluations are recorded yet.
    """
    import os, re
    import numpy as np

    jobs_folder = os.path.join(os.path.abspath(analysis_folder), "optimized", "jobs")
    if not os.path.isdir(jobs_folder):
        return []

    all_fvals = []
    for jobid in sorted(os.listdir(jobs_folder)):
        cb = os.path.join(jobs_folder, jobid, "callback.txt")
        if not os.path.exists(cb):
            continue
        content = open(cb, encoding="utf-8", errors="replace").read()
        fvals = [float(m) for m in re.findall(r"^f=([\-\d.eE+]+)", content, re.MULTILINE)]
        all_fvals.extend(fvals)

    if not all_fvals:
        return []

    best_so_far = np.minimum.accumulate(all_fvals)
    sv_so_far = -200 / (1 + np.exp(-1.5 * best_so_far)) + 100
    return [float(v) for v in sv_so_far]


def check_progress(run_info_or_folder, label=None, write_snapshot=False):
    """Read callback.txt(s) from all jobs and report best SV so far.

    Re-runnable at any time while the optimizer is running or after it
    completes.  Accepts either a ``RunInfo`` object or a plain folder path
    string, so it works even when the caller holds an older ``RunInfo``
    instance from a previous session.

    Parameters
    ----------
    run_info_or_folder : RunInfo or str
        A ``RunInfo`` object (uses its ``analysis_folder`` attribute) or
        a plain ``analysis_folder`` path string.
    label : str, optional
        Display label prefix. Defaults to the basename of the analysis folder.
    write_snapshot : bool, optional
        If ``True``, write a compact JSON file to
        ``<analysis_folder>/optimized/progress_snapshot.json`` in addition to
        printing.  The file can be read back later — even from a new AI session
        — via :meth:`RunInfo.load_progress_snapshot` or ``json.load(open(...))``::

            _run_sub.check_progress(write_snapshot=True)
            snap = _run_sub.load_progress_snapshot()  # dict

        Default ``False`` (print-only, no side effects).

    Returns
    -------
    dict or None
        Progress data dict when there are evaluations to report; ``None``
        otherwise.  Keys: ``label``, ``n_evals``, ``best_fv``, ``best_sv``,
        ``sv_best_so_far`` (full list), ``timestamp`` (ISO 8601 UTC).

    Examples
    --------
    ::

        # Via the RunInfo method (requires current class):
        _run_sub.check_progress(label="subprocess")

        # Persist for later AI-session retrieval:
        snap = _run_sub.check_progress(write_snapshot=True)

        # Via the standalone function (works with any RunInfo or a folder path):
        from molass.Rigorous import check_progress
        check_progress(_run_sub, label="subprocess")
        check_progress("/path/to/analysis_folder")  # plain string also accepted
    """
    import os
    import numpy as np

    # Accept RunInfo instance or plain string
    if isinstance(run_info_or_folder, str):
        analysis_folder = run_info_or_folder
    else:
        analysis_folder = getattr(run_info_or_folder, 'analysis_folder', None)
        if analysis_folder is None:
            print("check_progress: no analysis_folder set on this RunInfo")
            return

    if label is None:
        label = os.path.basename(analysis_folder.rstrip("/\\"))

    jobs_folder = os.path.join(os.path.abspath(analysis_folder), "optimized", "jobs")
    if not os.path.isdir(jobs_folder):
        print(f"{label}: jobs folder not yet created at:\n  {jobs_folder}")
        return

    sv_so_far = parse_sv_history(analysis_folder)
    if not sv_so_far:
        print(f"{label}: no f= lines yet in {jobs_folder}")
        return

    best_sv = sv_so_far[-1]  # last value of min-so-far = global best
    # Invert SV = -200/(1+exp(-1.5*fv))+100  →  fv = -ln(200/(100-SV)-1)/1.5
    best_fv = -np.log(200.0 / (100.0 - best_sv) - 1.0) / 1.5

    print(f"{label}: {len(sv_so_far)} evaluations")
    print(f"  best fv = {best_fv:.4f}  \u2192  SV = {best_sv:.2f}")
    print(f"  SV best-so-far (last 10): {[round(v, 2) for v in sv_so_far[-10:]]}")

    from datetime import datetime, timezone
    snapshot = {
        "label": label,
        "n_evals": len(sv_so_far),
        "best_fv": float(best_fv),
        "best_sv": float(best_sv),
        "sv_best_so_far": sv_so_far,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if write_snapshot:
        import json
        snapshot_path = os.path.join(
            os.path.abspath(analysis_folder), "optimized", "progress_snapshot.json"
        )
        with open(snapshot_path, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh, indent=2)
        print(f"  snapshot written → {snapshot_path}")

    return snapshot


def read_convergence_data(analysis_folder):
    """Read convergence data from all completed rigorous optimization jobs.

    Parameters
    ----------
    analysis_folder : str
        The same ``analysis_folder`` passed to ``optimize_rigorously()``.

    Returns
    -------
    ConvergenceInfo
        Summary with per-job trajectories and cross-job diagnostics.
        Key fields for programmatic assessment:

        - ``best_fv`` — global best objective value
        - ``spread`` — difference between worst and best job's best_fv
        - ``trend`` — ``'improving'``, ``'worsening'``, or ``'stable'``
        - ``jobs`` — list of ``JobConvergence`` with full fv trajectories

    Examples
    --------
    ::

        info = Decomposition.plot_convergence("temp_analysis")
        print(f"Best fv: {info.best_fv:.4f}, spread: {info.spread:.6f}")
        print(f"Trend: {info.trend}")
    """
    import numpy as np
    from molass_legacy.Optimizer.StateSequence import read_callback_txt_impl

    analysis_folder = os.path.abspath(analysis_folder)
    jobs_folder = os.path.join(analysis_folder, "optimized", "jobs")

    if not os.path.exists(jobs_folder):
        raise FileNotFoundError(f"No jobs folder found at {jobs_folder}")

    job_convergences = []
    for d in sorted(os.listdir(jobs_folder)):
        job_dir = os.path.join(jobs_folder, d)
        if not os.path.isdir(job_dir):
            continue
        cb_file = os.path.join(job_dir, "callback.txt")
        if not os.path.exists(cb_file):
            continue

        fv_list, _ = read_callback_txt_impl(cb_file)
        if not fv_list:
            continue

        evals = [row[0] for row in fv_list]
        fvs = [row[1] for row in fv_list]
        timestamps = [row[3] for row in fv_list]
        best_fv = min(fvs)

        job_convergences.append(JobConvergence(
            id=d, evals=evals, fvs=fvs, best_fv=best_fv,
            best_sv=float(fv_to_sv(best_fv)), timestamps=timestamps,
        ))

    if not job_convergences:
        raise FileNotFoundError(f"No completed jobs found in {jobs_folder}")

    best_fvs = [j.best_fv for j in job_convergences]
    global_best = min(best_fvs)
    best_job_id = job_convergences[np.argmin(best_fvs)].id
    spread = max(best_fvs) - min(best_fvs)

    # Trend: compare first half vs second half averages
    n = len(best_fvs)
    if n < 2:
        trend = 'stable'
    else:
        first_half = np.mean(best_fvs[:n // 2])
        second_half = np.mean(best_fvs[n // 2:])
        if second_half < first_half - 1e-6:
            trend = 'improving'
        elif second_half > first_half + 1e-6:
            trend = 'worsening'
        else:
            trend = 'stable'

    return ConvergenceInfo(
        jobs=job_convergences,
        best_fv=global_best,
        best_sv=float(fv_to_sv(global_best)),
        best_job_id=best_job_id,
        spread=spread,
        trend=trend,
        n_jobs=len(job_convergences),
    )


def plot_convergence(analysis_folder, ax=None, title=None):
    """Plot convergence across rigorous optimization jobs.

    Left subplot: best fv per job (cross-job trend).
    Right subplot: fv trajectory within each job (overlaid).

    Parameters
    ----------
    analysis_folder : str
        The same ``analysis_folder`` passed to ``optimize_rigorously()``.
    ax : matplotlib Axes or array of Axes, optional
        If provided, plot into these axes (expects 2 axes).
        If ``None``, creates a new figure with 2 subplots.
    title : str, optional
        Figure title. If ``None``, uses a default.

    Returns
    -------
    ConvergenceInfo
        The convergence data (same as ``read_convergence_data()``),
        so the caller can inspect values programmatically.

    Examples
    --------
    ::

        info = Decomposition.plot_convergence("temp_analysis")
        print(f"Best: {info.best_fv:.4f}, trend: {info.trend}")
    """
    import matplotlib
    import matplotlib.pyplot as plt
    import numpy as np

    info = read_convergence_data(analysis_folder)

    if ax is None:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    else:
        axes = np.asarray(ax).ravel()
        fig = axes[0].figure

    ax1, ax2 = axes[0], axes[1]

    # Left: best SV per job
    job_ids = [j.id for j in info.jobs]
    best_svs = [j.best_sv for j in info.jobs]
    x_pos = range(len(job_ids))
    colors = ['forestgreen' if sv >= 80 else 'steelblue' if sv >= 60 else 'salmon'
              for sv in best_svs]
    ax1.bar(x_pos, best_svs, color=colors, alpha=0.8)
    best_idx = np.argmax(best_svs)
    ax1.bar(best_idx, best_svs[best_idx], color='orange', alpha=0.9)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(job_ids, rotation=45, fontsize=8)
    ax1.set_xlabel('Job')
    ax1.set_ylabel('SV (Score Value)')
    # Zoom y-axis to data range so small differences are visible
    sv_min, sv_max = min(best_svs), max(best_svs)
    sv_range = sv_max - sv_min if sv_max != sv_min else max(abs(sv_min), 1) * 0.01
    pad = sv_range * 0.3
    ax1.set_ylim(sv_min - pad, sv_max + pad)
    # Reference line at SV=80
    if sv_min - pad <= 80 <= sv_max + pad:
        ax1.axhline(80, color='green', linestyle='--', alpha=0.5, linewidth=1)
        ax1.text(len(job_ids) - 0.5, 80.5, 'good', fontsize=7, color='green', alpha=0.7)
    sv_spread = sv_max - sv_min
    ax1.set_title(f'Best SV per job (spread={sv_spread:.2f}, {info.trend})')

    # Right: SV trajectory — skip initial transient, zoom to converged region
    cmap = plt.cm.viridis
    n = len(info.jobs)
    all_final_svs = []
    for job in info.jobs:
        running_min_fv = np.minimum.accumulate(job.fvs)
        running_sv = fv_to_sv(running_min_fv)
        n_pts = len(running_sv)
        start = max(1, n_pts // 5)
        all_final_svs.extend(running_sv[start:].tolist())
    conv_min = min(all_final_svs) if all_final_svs else 0
    conv_max = max(all_final_svs) if all_final_svs else 100
    conv_range = conv_max - conv_min if conv_max != conv_min else max(abs(conv_min), 1) * 0.01
    for i, job in enumerate(info.jobs):
        color = cmap(i / max(n - 1, 1))
        running_min_fv = np.minimum.accumulate(job.fvs)
        running_sv = fv_to_sv(running_min_fv)
        ax2.plot(range(len(running_sv)), running_sv,
                 color=color, alpha=0.7, linewidth=1, label=job.id)
    # Zoom y-axis to converged region with padding
    y_pad = conv_range * 0.3
    ax2.set_ylim(conv_min - y_pad, conv_max + y_pad)
    # Reference line at SV=80 if in range
    if conv_min - y_pad <= 80 <= conv_max + y_pad:
        ax2.axhline(80, color='green', linestyle='--', alpha=0.5, linewidth=1)
    ax2.set_xlabel('Iteration')
    ax2.set_ylabel('Running best SV')
    ax2.set_title('Per-job convergence (zoomed)')
    if n <= 15:
        ax2.legend(fontsize=7, ncol=2, loc='upper right')

    if title is None:
        title = f'Convergence: {info.n_jobs} jobs, best SV={info.best_sv:.1f}'
    fig.suptitle(title, fontsize=13)
    fig.tight_layout()

    # Show the figure: use IPython display in notebooks, plt.show() elsewhere
    def _in_notebook():
        try:
            from IPython import get_ipython
            shell = get_ipython()
            return shell is not None and 'IPKernelApp' in shell.config
        except Exception:
            return False

    if _in_notebook():
        from IPython.display import display
        display(fig)
        plt.close(fig)
    else:
        from molass.Testing import is_interactive
        if is_interactive():
            plt.show()

    # Print summary for programmatic assessment
    quality = 'GOOD' if info.best_sv >= 80 else 'fair' if info.best_sv >= 60 else 'poor'
    print(f"Jobs: {info.n_jobs} | Best SV: {info.best_sv:.1f} ({quality}) | fv: {info.best_fv:.6f} (job {info.best_job_id})")
    sv_spread = max(j.best_sv for j in info.jobs) - min(j.best_sv for j in info.jobs)
    print(f"SV spread: {sv_spread:.2f} | Trend: {info.trend}")
    for j in info.jobs:
        print(f"  {j.id}: {len(j.fvs)} iters, SV={j.best_sv:.1f}, fv={j.best_fv:.6f}")

    return info