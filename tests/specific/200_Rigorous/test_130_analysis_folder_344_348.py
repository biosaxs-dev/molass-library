"""
Analysis-folder helpers: rejected iterations and stalled jobs (#346), manifest status derived from the
disk (#345), data folder resolution (#348) and the JobInfo / AnalysisInfo plumbing of load_analysis (#344).
Synthetic folders only, no optimizer is run.
"""
import json
import os
import time

import pytest

from molass.Rigorous.CurrentStateUtils import JobInfo, count_stalled_jobs, list_rigorous_jobs
from molass.Rigorous.RunRegistry import (
    MANIFEST_NAME, read_manifest, refresh_run_manifest, write_run_manifest, locate_recent_runs,
)


def _write_job(folder, jobid, fvs):
    job_dir = os.path.join(folder, "optimized", "jobs", jobid)
    os.makedirs(job_dir, exist_ok=True)
    with open(os.path.join(job_dir, "callback.txt"), "w") as f:
        for i, fv in enumerate(fvs):
            f.write(f"t=2026-01-01 12:00:{i:02d}\n")
            f.write("x=\n[ 1.0]\n")
            f.write(f"f={fv}\n")
            f.write(f"a={'True' if i else 'False'}\n")
            f.write(f"c={i * 1000}\n")
    return job_dir


def _age(job_dir, seconds):
    t = time.time() - seconds
    for name in os.listdir(job_dir):
        os.utime(os.path.join(job_dir, name), (t, t))


def _set_manifest_time(folder, seconds_ago):
    from datetime import datetime, timedelta, timezone
    path = os.path.join(folder, MANIFEST_NAME)
    with open(path) as f:
        manifest = json.load(f)
    manifest["start_time"] = (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat(timespec="seconds")
    with open(path, "w") as f:
        json.dump(manifest, f)


def test_job_info_counts_nonfinite(tmp_path):
    _write_job(str(tmp_path), "000", [-1.4, "inf", -1.5, "inf", "inf", -1.6])
    (job,) = list_rigorous_jobs(str(tmp_path))
    assert job.n_entries == job.iterations == 6
    assert job.n_nonfinite == 3
    assert job.best_fv == pytest.approx(-1.6)


def test_job_info_keeps_four_field_construction():
    job = JobInfo("000", 5, -1.0, None)
    assert job.n_nonfinite == 0


def test_count_stalled_jobs():
    jobs = [JobInfo(str(i), 10, fv, None) for i, fv in enumerate([-1.511, -1.574, -1.574, -1.574])]
    assert count_stalled_jobs(jobs) == 2
    assert count_stalled_jobs(jobs[:2]) == 0
    assert count_stalled_jobs([]) == 0
    improving = [JobInfo(str(i), 10, fv, None) for i, fv in enumerate([-1.0, -1.2, -1.5])]
    assert count_stalled_jobs(improving) == 0


def test_refresh_running_manifest_of_finished_run(tmp_path):
    folder = str(tmp_path)
    write_run_manifest(folder, status="running", phase="optimizer_ready")
    job_dir = _write_job(folder, "000", [-1.4, -1.5, "inf"])
    _age(job_dir, 7200)

    manifest = refresh_run_manifest(folder)
    assert manifest["status"] == "completed"
    assert manifest["phase"] == "finished"
    assert manifest["n_jobs"] == 1 and manifest["n_nonfinite"] == 1
    assert manifest["best_fv"] == pytest.approx(-1.5)
    assert read_manifest(folder)["status"] == "completed"   # persisted


def test_refresh_completed_manifest_with_new_jobs_is_running(tmp_path):
    folder = str(tmp_path)
    write_run_manifest(folder, status="completed", phase="optimizer_ready")
    _set_manifest_time(folder, 3600)             # completion was recorded an hour ago
    _write_job(folder, "000", [-1.4, -1.5])      # just written: a chained job is going on
    assert refresh_run_manifest(folder)["status"] == "running"


def test_refresh_keeps_completed_manifest_of_run_that_just_ended(tmp_path):
    folder = str(tmp_path)
    _write_job(folder, "000", [-1.4, -1.5])
    time.sleep(2.1)
    write_run_manifest(folder, status="completed")   # written after the last job file
    assert refresh_run_manifest(folder)["status"] == "completed"


def test_refresh_keeps_failed_and_new_runs(tmp_path):
    failed = str(tmp_path / "failed")
    os.makedirs(failed)
    write_run_manifest(failed, status="failed", subprocess_returncode=1)
    _age(_write_job(failed, "000", [-1.4, -1.5]), 7200)
    assert refresh_run_manifest(failed)["status"] == "failed"

    new = str(tmp_path / "new")
    os.makedirs(os.path.join(new, "optimized", "jobs"))
    write_run_manifest(new, status="starting", phase="folders_prepared")
    assert refresh_run_manifest(new)["status"] == "starting"


def test_refresh_ignores_folders_without_jobs(tmp_path):
    folder = str(tmp_path)
    write_run_manifest(folder, role="work", status="running")
    assert refresh_run_manifest(folder) is None
    assert "n_jobs" not in read_manifest(folder)


def test_read_manifest_refresh_flag(tmp_path):
    folder = str(tmp_path)
    write_run_manifest(folder, status="running")
    _age(_write_job(folder, "000", [-1.4, -1.5]), 7200)
    assert read_manifest(folder)["status"] == "running"
    assert read_manifest(folder, refresh=True)["status"] == "completed"


def test_locate_recent_runs_refreshes(tmp_path, monkeypatch):
    folder = str(tmp_path / "run")
    os.makedirs(folder)
    manifest = write_run_manifest(folder, status="running")
    _age(_write_job(folder, "000", [-1.4, -1.5]), 7200)
    registry = tmp_path / "runs.jsonl"
    registry.write_text(json.dumps({"folder": folder, "start_time": manifest["start_time"]}) + "\n")
    (run,) = locate_recent_runs(registry_path=str(registry))
    assert run["manifest"]["status"] == "completed"
    (run,) = locate_recent_runs(registry_path=str(registry), refresh=False)
    assert run["manifest"]["status"] == "completed"   # already persisted by the first call


def test_live_status_reports_rejected_iterations(tmp_path):
    from molass.Rigorous.RunInfo import RunInfo
    folder = str(tmp_path)
    for jobid, fvs in (("000", [-1.3, "inf", -1.5]), ("001", [-1.5, "inf", "inf"]), ("002", [-1.5, -1.4])):
        _write_job(folder, jobid, fvs)
    ri = RunInfo(ssd=None, optimizer=None, dsets=None, init_params=None, analysis_folder=folder)
    status = ri.live_status()
    assert status["n_jobs"] == 3
    assert status["n_entries"] == 8
    assert status["n_nonfinite"] == 3
    assert status["stalled_jobs"] == 2


def _recipe_folder(tmp_path, stored=None):
    folder = tmp_path / "analysis"
    job = folder / "optimized" / "jobs" / "000"
    job.mkdir(parents=True)
    if stored is not None:
        (job / "in_folder.txt").write_text(stored)
    return str(folder)


def test_resolve_input_folder_override_and_stored(tmp_path):
    from molass.Rigorous.RecipeRunner import resolve_input_folder
    data = tmp_path / "data"
    data.mkdir()
    folder = _recipe_folder(tmp_path, stored=str(data))
    assert resolve_input_folder(folder, {}) == str(data)

    other = tmp_path / "other"
    other.mkdir()
    assert resolve_input_folder(folder, {}, in_folder=str(other)) == str(other)
    with pytest.raises(FileNotFoundError):
        resolve_input_folder(folder, {}, in_folder=str(tmp_path / "missing"))


def test_resolve_input_folder_missing_names_path_and_override(tmp_path):
    from molass.Rigorous.RecipeRunner import resolve_input_folder
    gone = r"D:\elsewhere\my_data"
    folder = _recipe_folder(tmp_path, stored=gone)
    with pytest.raises(FileNotFoundError) as excinfo:
        resolve_input_folder(folder, {})
    assert gone in str(excinfo.value) and "in_folder" in str(excinfo.value)


def test_resolve_input_folder_bundled_sample_on_another_machine(tmp_path):
    molass_data = pytest.importorskip("molass_data")
    from molass.Rigorous.RecipeRunner import resolve_input_folder, bundled_dataset_name
    assert bundled_dataset_name(molass_data.SAMPLE1) == "SAMPLE1"
    assert bundled_dataset_name(str(tmp_path)) is None

    # the stored path points into the molass_data of the machine that made the analysis
    folder = _recipe_folder(tmp_path, stored=r"Z:\no\such\site-packages\molass_data\SAMPLE1")
    assert resolve_input_folder(folder, {}) == molass_data.SAMPLE1
    # a recorded dataset name wins, and needs no job at all
    bare = str(tmp_path / "bare")
    os.makedirs(bare)
    assert resolve_input_folder(bare, {"dataset": "SAMPLE1"}) == molass_data.SAMPLE1


def test_resolve_input_folder_relocated_temp_in_folder(tmp_path):
    from molass.Rigorous.RecipeRunner import resolve_input_folder
    folder = _recipe_folder(tmp_path, stored=r"E:\old_place\analysis\temp_in_folder")
    export = os.path.join(folder, "temp_in_folder")
    os.makedirs(export)
    assert resolve_input_folder(folder, {}) == export


def test_recipe_records_bundled_dataset(tmp_path):
    from types import SimpleNamespace
    from molass.Rigorous.RigorousImplement import build_pipeline_recipe
    molass_data = pytest.importorskip("molass_data")

    def recipe_for(folder):
        ssd = SimpleNamespace(datafiles=[os.path.join(folder, "PREFIX_00000.dat")], uv=None, xr=None, trimming=None)
        return build_pipeline_recipe(None, model="egh", num_components=2, ssd=ssd)

    assert recipe_for(molass_data.SAMPLE3)["dataset"] == "SAMPLE3"
    assert "dataset" not in recipe_for(str(tmp_path))


def test_analysis_info_summary():
    from molass.Rigorous.AnalysisFolder import AnalysisInfo
    jobs = [JobInfo("000", 5, -1.5, None, 5, 1), JobInfo("001", 4, -1.5, None, 4, 0)]

    class _Result:
        fv, sv = -1.5, 77.0

    info = AnalysisInfo("analysis-001", _Result(), "000", None, None, None,
                        {"model": "edm", "num_components": 3}, jobs, {"status": "completed", "phase": "finished"})
    assert (info.n_jobs, info.n_iterations, info.n_nonfinite, info.stalled_jobs) == (2, 9, 1, 1)
    assert info.best_job.id == "000"
    text = str(info)
    assert "job 000" in text and "sv=77.00" in text and "rejected (non-finite): 1" in text
