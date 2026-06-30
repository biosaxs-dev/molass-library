"""Test Decomposition.plot_convergence() and read_convergence_data().

Run standalone:  python tests/specific/test_plot_convergence.py
Run via pytest:  python -m pytest tests/specific/test_plot_convergence.py -p no:order
"""
import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import numpy as np
import pytest


def _make_callback_txt(job_dir, fv_values, start_counter=0):
    """Write a minimal callback.txt with given fv values."""
    os.makedirs(job_dir, exist_ok=True)
    cb_path = os.path.join(job_dir, "callback.txt")
    with open(cb_path, "w") as f:
        for i, fv in enumerate(fv_values):
            t = datetime(2026, 4, 13, 12, 0, i)
            f.write(f"t={t.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("x=\n")
            params = " ".join([f"{v:.4f}" for v in np.random.default_rng(i).standard_normal(5)])
            f.write(f"[{params}]\n")
            f.write(f"f={fv}\n")
            f.write(f"a=True\n")
            f.write(f"c={start_counter + (i + 1) * 100}\n")


def _make_analysis_folder(tmpdir, n_jobs=5, improving=True):
    """Create a fake analysis folder with n_jobs."""
    for j in range(n_jobs):
        job_dir = os.path.join(tmpdir, "optimized", "jobs", f"{j:03d}")
        offset = -0.1 * j if improving else 0.1 * j
        fvs = [10.0 + offset - 0.01 * i for i in range(10)]
        _make_callback_txt(job_dir, fvs)
    return tmpdir


def test_read_basic():
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=5, improving=True)
        from molass.Rigorous.CurrentStateUtils import read_convergence_data
        info = read_convergence_data(af)
        assert info.n_jobs == 5
        assert info.best_fv < 10.0
        assert info.best_sv is not None
        assert info.spread > 0
        assert info.trend == 'improving'
        assert info.best_job_id == '004'


def test_read_worsening():
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=5, improving=False)
        from molass.Rigorous.CurrentStateUtils import read_convergence_data
        info = read_convergence_data(af)
        assert info.trend == 'worsening'
        assert info.best_job_id == '000'


def test_read_single_job():
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=1)
        from molass.Rigorous.CurrentStateUtils import read_convergence_data
        info = read_convergence_data(af)
        assert info.n_jobs == 1
        assert info.spread == 0.0
        assert info.trend == 'stable'


def test_per_job_detail():
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=3)
        from molass.Rigorous.CurrentStateUtils import read_convergence_data
        info = read_convergence_data(af)
        for job in info.jobs:
            assert len(job.fvs) == 10
            assert len(job.evals) == 10
            assert job.best_fv == min(job.fvs)
            assert job.best_sv is not None


def test_missing_folder_raises():
    from molass.Rigorous.CurrentStateUtils import read_convergence_data
    with pytest.raises(FileNotFoundError):
        read_convergence_data("/nonexistent/path")


def test_plot_returns_info():
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=4)
        from molass.Rigorous.CurrentStateUtils import plot_convergence
        info = plot_convergence(af)
        assert info.n_jobs == 4
        assert info.best_fv is not None


def test_plot_via_decomposition():
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=3)
        from molass.LowRank.Decomposition import Decomposition
        info = Decomposition.plot_convergence(af)
        assert info.n_jobs == 3


def test_plot_custom_axes():
    import matplotlib.pyplot as plt
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=3)
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        from molass.Rigorous.CurrentStateUtils import plot_convergence
        info = plot_convergence(af, ax=axes)
        assert info.n_jobs == 3
        plt.close(fig)


# --- check_progress tests (issue #123) ---

def test_check_progress_basic(capsys):
    """check_progress prints evaluation count and best SV."""
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=2, improving=True)
        from molass.Rigorous import check_progress
        check_progress(af)   # plain folder-path string
        out = capsys.readouterr().out
        assert "evaluations" in out
        assert "SV" in out


def test_check_progress_with_label(capsys):
    """label= prefix appears in output."""
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=1)
        from molass.Rigorous import check_progress
        check_progress(af, label="myrun")
        out = capsys.readouterr().out
        assert out.startswith("myrun:")


def test_check_progress_run_info(capsys):
    """check_progress accepts a RunInfo-like object with .analysis_folder."""
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=3)

        class _FakeRunInfo:
            analysis_folder = af

        from molass.Rigorous import check_progress
        check_progress(_FakeRunInfo(), label="fake")
        out = capsys.readouterr().out
        assert "fake:" in out
        assert "evaluations" in out


def test_check_progress_empty_folder(capsys):
    """No callback.txt yet — prints a helpful message, does not raise."""
    with tempfile.TemporaryDirectory() as td:
        jobs = os.path.join(td, "optimized", "jobs", "000")
        os.makedirs(jobs, exist_ok=True)   # folder exists but no callback.txt
        from molass.Rigorous import check_progress
        check_progress(td, label="empty")
        out = capsys.readouterr().out
        assert "no f= lines" in out


def test_check_progress_missing_jobs_folder(capsys):
    """optimized/jobs/ not yet created — prints a helpful message, does not raise."""
    with tempfile.TemporaryDirectory() as td:
        from molass.Rigorous import check_progress
        check_progress(td, label="notstarted")
        out = capsys.readouterr().out
        assert "jobs folder not yet created" in out


def test_check_progress_run_info_no_folder(capsys):
    """RunInfo with analysis_folder=None — prints a helpful message, does not raise."""
    class _FakeRunInfo:
        analysis_folder = None

    from molass.Rigorous import check_progress
    check_progress(_FakeRunInfo())
    out = capsys.readouterr().out
    assert "no analysis_folder" in out


# --- write_snapshot / load_progress_snapshot tests (issue #124) ---

def test_check_progress_returns_dict():
    """check_progress returns a dict with expected keys."""
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=2)
        from molass.Rigorous import check_progress
        result = check_progress(af)
        assert isinstance(result, dict)
        for key in ("label", "n_evals", "best_fv", "best_sv", "sv_best_so_far", "timestamp"):
            assert key in result, f"missing key: {key}"
        assert result["n_evals"] == 20   # 2 jobs × 10 evals each
        assert isinstance(result["best_sv"], float)
        assert -200 < result["best_sv"] < 100


def test_check_progress_write_snapshot(capsys):
    """write_snapshot=True creates progress_snapshot.json and mentions the path."""
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=2)
        from molass.Rigorous import check_progress
        snap_path = os.path.join(os.path.abspath(af), "optimized", "progress_snapshot.json")
        assert not os.path.exists(snap_path), "should not exist before call"
        check_progress(af, write_snapshot=True)
        assert os.path.exists(snap_path), "JSON file should be written"
        out = capsys.readouterr().out
        assert "snapshot written" in out


def test_check_progress_snapshot_content():
    """Written JSON has correct keys and plausible values."""
    import json
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=3)
        from molass.Rigorous import check_progress
        returned = check_progress(af, write_snapshot=True)
        snap_path = os.path.join(os.path.abspath(af), "optimized", "progress_snapshot.json")
        on_disk = json.load(open(snap_path, encoding="utf-8"))
        # Returned dict and on-disk JSON must agree
        assert on_disk["n_evals"] == returned["n_evals"]
        assert abs(on_disk["best_sv"] - returned["best_sv"]) < 1e-9
        assert len(on_disk["sv_best_so_far"]) == on_disk["n_evals"]
        assert "T" in on_disk["timestamp"]  # ISO 8601 includes "T"


def test_load_progress_snapshot_via_run_info():
    """RunInfo.load_progress_snapshot() reads back what check_progress wrote."""
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=2)
        from molass.Rigorous.RunInfo import RunInfo

        class _FakeRunInfo(RunInfo):
            pass

        ri = object.__new__(_FakeRunInfo)
        ri.analysis_folder = af
        ri.check_progress(write_snapshot=True)
        snap = ri.load_progress_snapshot()
        assert isinstance(snap, dict)
        assert snap["n_evals"] == 20
        assert -200 < snap["best_sv"] < 100


def test_load_progress_snapshot_missing_raises():
    """load_progress_snapshot raises FileNotFoundError if snapshot absent."""
    with tempfile.TemporaryDirectory() as td:
        af = _make_analysis_folder(td, n_jobs=1)
        from molass.Rigorous.RunInfo import RunInfo

        ri = object.__new__(RunInfo)
        ri.analysis_folder = af
        with pytest.raises(FileNotFoundError):
            ri.load_progress_snapshot()


def test_progress_snapshot_json_path_property():
    """progress_snapshot_json_path returns expected path or None."""
    import os
    from molass.Rigorous.RunInfo import RunInfo

    ri = object.__new__(RunInfo)
    ri.analysis_folder = None
    assert ri.progress_snapshot_json_path is None

    ri.analysis_folder = "/some/folder"
    p = ri.progress_snapshot_json_path
    assert p.endswith(os.path.join("optimized", "progress_snapshot.json"))


if __name__ == '__main__':
    for name, func in list(globals().items()):
        if name.startswith('test_') and callable(func):
            func()
            print(f"{name}: OK")
    print("\nALL TESTS PASSED")
