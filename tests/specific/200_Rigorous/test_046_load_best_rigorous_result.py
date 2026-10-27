"""molass-library#336: one call to load the best (not the latest) on-disk rigorous result."""
import os

import pytest

import molass.Rigorous.CurrentStateUtils as csu
from molass.Rigorous import load_best_rigorous_result


class _Stop(Exception):
    pass


def _jobs(*pairs):
    return [csu.JobInfo(id=i, iterations=10, best_fv=fv, timestamp=0.0) for i, fv in pairs]


@pytest.fixture
def stop_at_params(monkeypatch):
    """Stop right after the job is chosen, reporting the folder that would be loaded."""
    def fake_get_params(job_result_folder, debug=False):
        raise _Stop(os.path.basename(job_result_folder))
    monkeypatch.setattr(csu, "get_params", fake_get_params)


def test_best_job_is_chosen_not_the_latest(monkeypatch, stop_at_params, tmp_path):
    monkeypatch.setattr(csu, "list_rigorous_jobs", lambda folder: _jobs(("000", 0.9), ("001", 0.2), ("002", 0.5)))
    with pytest.raises(_Stop, match="001"):
        load_best_rigorous_result(object(), str(tmp_path))
    with pytest.raises(_Stop, match="002"):             # the existing default stays the latest job
        csu.load_rigorous_result(object(), str(tmp_path))


def test_jobid_best_equals_the_function(monkeypatch, stop_at_params, tmp_path):
    monkeypatch.setattr(csu, "list_rigorous_jobs", lambda folder: _jobs(("000", 0.3), ("001", 0.8)))
    with pytest.raises(_Stop, match="000"):
        csu.load_rigorous_result(object(), str(tmp_path), jobid="best")


def test_explicit_jobid_is_untouched(monkeypatch, stop_at_params, tmp_path):
    monkeypatch.setattr(csu, "list_rigorous_jobs", lambda folder: _jobs(("000", 0.3), ("001", 0.8)))
    with pytest.raises(_Stop, match="001"):
        csu.load_rigorous_result(object(), str(tmp_path), jobid="001")


def test_no_completed_job_raises_a_clear_error(monkeypatch, tmp_path):
    monkeypatch.setattr(csu, "list_rigorous_jobs", lambda folder: [])
    with pytest.raises(csu.NoCompletedJobError, match="No completed job"):
        load_best_rigorous_result(object(), str(tmp_path))
    with pytest.raises(FileNotFoundError):              # still a FileNotFoundError for existing handlers
        csu.load_rigorous_result(object(), str(tmp_path))
