"""
Rigorous.CurrentStateUtils.py
"""
import os
from collections import namedtuple
from molass_legacy._MOLASS.SerialSettings import get_setting
from molass_legacy.Optimizer.Scripting import get_params
from molass.LowRank.Decomposition import Decomposition
from molass.SEC.Models.UvComponentCurve import UvComponentCurve
from molass.Mapping.Mapping import Mapping

JobInfo = namedtuple('JobInfo', ['id', 'iterations', 'best_fv', 'timestamp'])
"""Metadata for a single rigorous optimization job.

Attributes
----------
id : str
    Job folder name (e.g. ``'000'``, ``'001'``).
iterations : int
    Number of iterations recorded in ``callback.txt``.
best_fv : float
    Best (minimum) objective function value across all iterations.
timestamp : datetime or None
    Timestamp of the last recorded iteration, or ``None`` if unavailable.
"""

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


def load_rigorous_result(decomp, analysis_folder, jobid=None, debug=False):
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
    from molass.Rigorous.LegacyBridgeUtils import (
        make_dsets_from_decomposition,
        make_basecurves_from_decomposition,
        construct_legacy_optimizer,
    )

    ssd = decomp.ssd
    rgcurve_for_dsets = ssd.xr.compute_rgcurve()
    dsets = make_dsets_from_decomposition(decomp, rgcurve_for_dsets, debug=debug)
    basecurves, _ = make_basecurves_from_decomposition(decomp, debug=debug)
    spectral_vectors = ssd.get_spectral_vectors()
    model = decomp.xr_ccurves[0].model

    optimizer = construct_legacy_optimizer(
        dsets, basecurves, spectral_vectors,
        num_components=decomp.num_components,
        model=model,
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

    return Decomposition(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves)


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