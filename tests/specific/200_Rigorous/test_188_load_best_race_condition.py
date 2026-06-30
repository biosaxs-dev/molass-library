"""
Test that list_rigorous_jobs() skips jobs with no accepted entries,
preventing load_best() from returning init params when called before
the first BH trial completes.

See: https://github.com/biosaxs-dev/molass-library/issues/188
"""
import os
import tempfile
import pytest


def _write_callback(job_dir, entries):
    """Write a minimal callback.txt with the given (fv, accepted) entries."""
    os.makedirs(job_dir, exist_ok=True)
    cb_path = os.path.join(job_dir, "callback.txt")
    with open(cb_path, "w") as f:
        for i, (fv, accepted) in enumerate(entries):
            f.write(f"t=2026-01-01 12:00:{i:02d}\n")
            f.write("x=\n[ 1.0]\n")
            f.write(f"f={fv}\n")
            f.write(f"a={'True' if accepted else 'False'}\n")
            f.write(f"c={i * 1000}\n")


def test_no_accepted_entries_excluded():
    """A job whose callback.txt has only the single a=False init entry must be excluded."""
    from molass.Rigorous.CurrentStateUtils import list_rigorous_jobs

    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_dir = os.path.join(tmpdir, "optimized", "jobs", "000")
        _write_callback(jobs_dir, [(-1.468, False)])  # init only (c=0)

        jobs = list_rigorous_jobs(tmpdir)
        assert jobs == [], "Expected no jobs when only the init entry exists"


def test_best_fv_across_all_entries():
    """best_fv must be the global minimum across ALL entries, regardless of a=True/False."""
    from molass.Rigorous.CurrentStateUtils import list_rigorous_jobs

    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_dir = os.path.join(tmpdir, "optimized", "jobs", "000")
        _write_callback(jobs_dir, [
            (-1.468, False),  # init
            (-1.614, True),   # first BH jump
            (-1.633, True),   # best
        ])

        jobs = list_rigorous_jobs(tmpdir)
        assert len(jobs) == 1
        assert abs(jobs[0].best_fv - (-1.633)) < 1e-6, \
            f"Expected best_fv=-1.633 (global min), got {jobs[0].best_fv}"


def test_cma_init_is_best_included():
    """CMA issue #194: init entry (a=False) IS the best result 窶・must be included.

    CMA marks its own generation improvements as a=True starting from an often-worse
    point.  The init params (from quick_decomposition) are frequently better than
    anything CMA finds.  best_fv must be the global min across all entries.
    """
    from molass.Rigorous.CurrentStateUtils import list_rigorous_jobs

    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_dir = os.path.join(tmpdir, "optimized", "jobs", "000")
        # CMA scenario: init is better than any CMA generation result
        _write_callback(jobs_dir, [
            (-1.4049, False),  # init (from quick_decomposition 窶・very good)
            (-1.3600, True),   # CMA generation 1 improvement (worse than init)
            (-1.3700, True),   # CMA generation 2 improvement (worse than init)
        ])

        jobs = list_rigorous_jobs(tmpdir)
        assert len(jobs) == 1
        assert abs(jobs[0].best_fv - (-1.4049)) < 1e-6, \
            f"Init fv must be included as best_fv when it is the global min, got {jobs[0].best_fv}"


def test_ns_all_false_entries_included():
    """NS jobs have all a=False (hardcoded in SamplerCallback). Must still be returned."""
    from molass.Rigorous.CurrentStateUtils import list_rigorous_jobs

    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_dir = os.path.join(tmpdir, "optimized", "jobs", "000")
        # NS: multiple callbacks, all a=False, best is -1.62
        _write_callback(jobs_dir, [
            (-1.468, False),  # c=0 init
            (-1.479, False),  # NS callback 1
            (-1.550, False),  # NS callback 2 (better)
            (-1.620, False),  # NS callback 3 (best)
        ])

        jobs = list_rigorous_jobs(tmpdir)
        assert len(jobs) == 1, "NS job must be included even though all a=False"
        assert abs(jobs[0].best_fv - (-1.620)) < 1e-6, \
            f"Expected best_fv=-1.620 for NS, got {jobs[0].best_fv}"
