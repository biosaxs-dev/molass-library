"""
Tests for parse_sv_history_per_job and RunInfo.sv_history_per_job.

See: https://github.com/biosaxs-dev/molass-library/issues/161
"""
import os
import tempfile
import pytest


def _write_callback(folder, fvals):
    """Write a callback.txt with the given fv values (all marked accepted)."""
    os.makedirs(folder, exist_ok=True)
    lines = []
    for i, fv in enumerate(fvals):
        lines.append(f"t=0\nx=\n[0.0]\nf={fv}\na=True\nc={i+1}\n")
    with open(os.path.join(folder, "callback.txt"), "w", encoding="utf-8") as f:
        f.write("".join(lines))


def _make_analysis_folder(tmp_path, jobs):
    """
    Create a fake analysis_folder structure.
    jobs: list of (job_id, fvals) tuples in order.
    """
    for job_id, fvals in jobs:
        job_dir = tmp_path / "optimized" / "jobs" / job_id
        _write_callback(str(job_dir), fvals)
    return str(tmp_path)


def test_single_job():
    """Single job: per-job dict has one entry matching sv_history."""
    from molass.Rigorous.CurrentStateUtils import parse_sv_history, parse_sv_history_per_job

    with tempfile.TemporaryDirectory() as tmp:
        folder = _make_analysis_folder(__import__('pathlib').Path(tmp), [
            ("000", [-2.0, -1.5, -1.8, -1.2]),
        ])
        merged = parse_sv_history(folder)
        per_job = parse_sv_history_per_job(folder)

    assert list(per_job.keys()) == ["000"]
    assert per_job["000"] == merged


def test_two_jobs_global_minimum_carries_over():
    """Second job inherits global best from job 000."""
    from molass.Rigorous.CurrentStateUtils import parse_sv_history, parse_sv_history_per_job
    import numpy as np

    with tempfile.TemporaryDirectory() as tmp:
        folder = _make_analysis_folder(__import__('pathlib').Path(tmp), [
            ("000", [-2.0, -1.0]),   # best after job 000 = -2.0
            ("001", [-1.5, -0.5]),   # -1.5 > -2.0 → global best stays -2.0; -0.5 > -2.0 → stays
        ])
        merged = parse_sv_history(folder)
        per_job = parse_sv_history_per_job(folder)

    # All entries in job 001 should equal the SV of fv=-2.0 (global best from job 000)
    sv_at_global_best = -200 / (1 + np.exp(-1.5 * -2.0)) + 100
    assert per_job["001"] == pytest.approx([sv_at_global_best, sv_at_global_best])

    # Concatenated per-job lists should equal the merged trajectory
    combined = per_job["000"] + per_job["001"]
    assert combined == pytest.approx(merged)


def test_job_with_improvement():
    """Second job that finds a better solution updates global best."""
    from molass.Rigorous.CurrentStateUtils import parse_sv_history, parse_sv_history_per_job

    with tempfile.TemporaryDirectory() as tmp:
        folder = _make_analysis_folder(__import__('pathlib').Path(tmp), [
            ("000", [-1.0]),
            ("001", [-3.0]),   # improvement over job 000
        ])
        per_job = parse_sv_history_per_job(folder)

    # job 001 should show a higher (better) SV than job 000's last entry
    assert per_job["001"][-1] > per_job["000"][-1]


def test_empty_analysis_folder():
    """No jobs folder → empty dict."""
    from molass.Rigorous.CurrentStateUtils import parse_sv_history_per_job

    with tempfile.TemporaryDirectory() as tmp:
        result = parse_sv_history_per_job(tmp)
    assert result == {}


def test_run_info_sv_history_per_job():
    """RunInfo.sv_history_per_job delegates to parse_sv_history_per_job."""
    from molass.Rigorous.RunInfo import RunInfo
    from unittest.mock import MagicMock, patch
    import tempfile, pathlib

    with tempfile.TemporaryDirectory() as tmp:
        folder = _make_analysis_folder(pathlib.Path(tmp), [
            ("000", [-2.0, -1.5]),
            ("001", [-2.5]),
        ])
        run_info = MagicMock(spec=RunInfo)
        run_info.analysis_folder = folder
        run_info.sv_history_per_job = property(
            lambda self: RunInfo.sv_history_per_job.fget(self)
        )
        result = RunInfo.sv_history_per_job.fget(run_info)

    assert set(result.keys()) == {"000", "001"}
    assert len(result["000"]) == 2
    assert len(result["001"]) == 1


def test_run_info_no_analysis_folder_raises():
    """RunInfo.sv_history_per_job raises ValueError when no analysis_folder."""
    from molass.Rigorous.RunInfo import RunInfo
    from unittest.mock import MagicMock

    run_info = MagicMock(spec=RunInfo)
    run_info.analysis_folder = None
    with pytest.raises(ValueError, match="analysis_folder"):
        RunInfo.sv_history_per_job.fget(run_info)
