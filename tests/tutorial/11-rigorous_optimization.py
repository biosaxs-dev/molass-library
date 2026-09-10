"""
Tests for the rigorous optimization tutorial (tutorial 11).
"""

import pytest
from molass.Testing import control_matplotlib_plot

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_quick_decomposition():
    from molass import requires
    requires('0.7.5')
    from molass_data import SAMPLE4
    from molass.DataObjects import SecSaxsData as SSD
    global decomposition, rgcurve
    ssd = SSD(SAMPLE4)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy()
    decomposition = corrected_ssd.quick_decomposition(proportions=[0.2, 0.5, 0.3])
    rgcurve = corrected_ssd.xr.compute_rgcurve()
    decomposition.plot_components(title="EGH Decomposition", rgcurve=rgcurve)

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_rigorous_optimization():
    from time import sleep
    import os
    from molass_legacy._MOLASS.SerialSettings import get_setting
    from molass_legacy.Optimizer.StateSequence import save_opt_params
    from molass_legacy.Optimizer.Scripting import get_params
    global run_info, decomposition, rgcurve
    if 'decomposition' not in globals():
        test_001_quick_decomposition()
    run_info = decomposition.optimize_rigorously(rgcurve=rgcurve, analysis_folder="temp_analysis_egh", method='NS', niter=20)
    current_decomposition = run_info.get_current_decomposition(wait_for_first_results=True)
    current_decomposition.plot_components(title="Rigorous Optimization Result", rgcurve=rgcurve)
    if run_info.monitor is not None:
        # monitor is None outside a Jupyter/IPython kernel (e.g. under pytest/CI)
        run_info.monitor.terminate()
    # wait_for_first_results only guarantees a single init-params entry, and NS is too
    # slow on CI to reliably add a 2nd real entry before termination above. Append one
    # synthetic accepted entry so has_rigorous_results/wait_for_rigorous_results (which
    # require >1 entries per issue #188) see a deterministically "complete" job.
    jobs_folder = os.path.join(get_setting('optimizer_folder'), "jobs")
    job_result_folder = os.path.join(jobs_folder, sorted(os.listdir(jobs_folder))[-1])
    x = get_params(job_result_folder)
    with open(os.path.join(job_result_folder, "callback.txt"), "a") as fh:
        save_opt_params(fh, x, -1.0, True, 1)

@pytest.mark.order(3)
def test_003_has_rigorous_results():
    from molass.LowRank.Decomposition import Decomposition
    # After test_002, results exist in temp_analysis_egh
    assert Decomposition.has_rigorous_results("temp_analysis_egh") is True
    # Non-existent folder should return False
    assert Decomposition.has_rigorous_results("nonexistent_folder_xyz") is False

@pytest.mark.order(4)
def test_004_wait_for_rigorous_results():
    from molass.LowRank.Decomposition import Decomposition
    # Already-existing results should return True immediately
    assert Decomposition.wait_for_rigorous_results("temp_analysis_egh", timeout=1) is True
    # Non-existent folder should time out and return False
    assert Decomposition.wait_for_rigorous_results("nonexistent_folder_xyz", timeout=1) is False
