"""
Rigorous.CurrentStateUtils.py
"""
import os
from molass_legacy._MOLASS.SerialSettings import get_setting
from molass_legacy.Optimizer.Scripting import get_params
from molass.LowRank.Decomposition import Decomposition
from molass.LowRank.ComponentCurve import ComponentCurve
from molass.SEC.Models.UvComponentCurve import UvComponentCurve
from molass.Mapping.Mapping import Mapping

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
    xr_params = separated_params[0]
    xr_ccurves = []
    x = xr_icurve.x
    for p in xr_params:
        xr_ccurves.append(ComponentCurve(x, p))

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
        xr_h = xr_ccurve.get_params()[0]
        uv_ccurves.append(UvComponentCurve(x, mapping, xr_ccurve, scale/xr_h))
    return Decomposition(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs)