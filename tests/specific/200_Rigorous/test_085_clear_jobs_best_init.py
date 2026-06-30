"""
Test that _load_best_init_params() correctly loads the best params from
previous jobs when clear_jobs=False.

See: https://github.com/biosaxs-dev/molass-library/issues/169
"""
import os
import tempfile
import numpy as np
import pytest

from molass.Rigorous.RigorousImplement import _load_best_init_params


def _write_callback_txt(folder, entries):
    """Write a minimal callback.txt with fv entries.

    entries: list of (counter, fv, x_array)
    """
    os.makedirs(folder, exist_ok=True)
    cb_path = os.path.join(folder, "callback.txt")
    with open(cb_path, "w") as f:
        import datetime
        for counter, fv, x in entries:
            f.write(f"t=2026-01-01 00:00:{counter:02d}\n")
            f.write("x=\n")
            f.write("[" + " ".join(str(v) for v in x) + "]\n")
            f.write(f"f={fv}\n")
            f.write("a=True\n")
            f.write(f"c={counter}\n")


def test_returns_none_when_no_jobs_dir():
    """No jobs dir → returns None (fallback to decomp params)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        analysis_folder = os.path.join(tmpdir, "analysis")
        os.makedirs(analysis_folder)
        init_params = np.zeros(10)
        result = _load_best_init_params(analysis_folder, init_params)
        assert result is None


def test_returns_none_when_jobs_dir_empty():
    """Empty jobs dir → returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        analysis_folder = os.path.join(tmpdir, "analysis")
        os.makedirs(os.path.join(analysis_folder, "optimized", "jobs"))
        init_params = np.zeros(10)
        result = _load_best_init_params(analysis_folder, init_params)
        assert result is None


def test_loads_best_from_single_job():
    """Single job with multiple entries → returns params of minimum fv."""
    with tempfile.TemporaryDirectory() as tmpdir:
        analysis_folder = os.path.join(tmpdir, "analysis")
        job_dir = os.path.join(analysis_folder, "optimized", "jobs", "000")
        good_x = [1.0, 2.0, 3.0, 4.0, 5.0]
        bad_x  = [9.1, 9.1, 9.1, 9.1, 9.1]
        _write_callback_txt(job_dir, [
            (1, -0.5, bad_x),
            (2, -1.2, good_x),   # best
            (3, -0.8, bad_x),
        ])
        init_params = np.zeros(5)
        result = _load_best_init_params(analysis_folder, init_params)
        assert result is not None
        np.testing.assert_array_almost_equal(result, good_x)


def test_loads_best_across_multiple_jobs():
    """Multiple jobs → returns params from the job/step with global minimum fv."""
    with tempfile.TemporaryDirectory() as tmpdir:
        analysis_folder = os.path.join(tmpdir, "analysis")
        job_a = os.path.join(analysis_folder, "optimized", "jobs", "000")
        job_b = os.path.join(analysis_folder, "optimized", "jobs", "001")
        x_a = [1.1, 1.1, 1.1, 1.1, 1.1]
        x_b = [2.2, 2.2, 2.2, 2.2, 2.2]  # best overall
        _write_callback_txt(job_a, [(1, -1.0, x_a)])
        _write_callback_txt(job_b, [(1, -1.5, x_b)])  # lower fv

        init_params = np.zeros(5)
        result = _load_best_init_params(analysis_folder, init_params)
        assert result is not None
        np.testing.assert_array_almost_equal(result, x_b)


def test_returns_none_when_length_mismatch():
    """Existing job has different param length → returns None (safety guard)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        analysis_folder = os.path.join(tmpdir, "analysis")
        job_dir = os.path.join(analysis_folder, "optimized", "jobs", "000")
        _write_callback_txt(job_dir, [(1, -1.0, [1.0, 2.0, 3.0])])

        init_params = np.zeros(10)  # different length
        result = _load_best_init_params(analysis_folder, init_params)
        assert result is None
