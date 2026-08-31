"""
Test that load_rigorous_result() skips incomplete jobs (only the single
init-params entry) when auto-selecting the latest job, instead of crashing
deep inside get_params() with a cryptic IndexError.

Found while building Decomposition.load_analysis_session() / "View Result":
a background GUI run's still-starting job (num_jobs round) crashed the
naive "last sorted job dir" auto-selection.

See: https://github.com/biosaxs-dev/molass-library/issues/188 (the original
     guard, already present in list_rigorous_jobs() but not load_rigorous_result())
"""
import os
import tempfile

from molass.Rigorous.CurrentStateUtils import load_rigorous_result


def _write_callback_txt(folder, entries):
    """entries: list of (counter, fv, x_array)"""
    os.makedirs(folder, exist_ok=True)
    cb_path = os.path.join(folder, "callback.txt")
    with open(cb_path, "w") as f:
        for counter, fv, x in entries:
            f.write(f"t=2026-01-01 00:00:{counter:02d}\n")
            f.write("x=\n")
            f.write("[" + " ".join(str(v) for v in x) + "]\n")
            f.write(f"f={fv}\n")
            f.write("a=True\n")
            f.write(f"c={counter}\n")


def test_skips_incomplete_latest_job(tmp_path):
    """The latest job dir has only 1 entry (still starting) -- must be skipped."""
    analysis_folder = str(tmp_path / "analysis")
    job_a = os.path.join(analysis_folder, "optimized", "jobs", "000")
    job_b = os.path.join(analysis_folder, "optimized", "jobs", "001")  # incomplete

    good_x = [1.0, 2.0, 3.0]
    _write_callback_txt(job_a, [(1, -0.5, good_x), (2, -1.2, good_x)])
    _write_callback_txt(job_b, [(1, -0.9, good_x)])  # only init entry

    class _FakeDecomp:
        pass

    # We only need to reach jobid resolution before it tries to use decomp's
    # attributes -- patch out the rest via a minimal fake and expect it to fail
    # further downstream (on decomp.ssd), not on the IndexError this guards.
    decomp = _FakeDecomp()
    try:
        load_rigorous_result(decomp, analysis_folder)
    except AttributeError as e:
        # Expected: got past jobid resolution (picked job "000", not "001"),
        # failed later on decomp.ssd (our fake has none) -- not an IndexError.
        assert "ssd" in str(e) or "'_FakeDecomp' object has no attribute" in str(e)
    else:
        raise AssertionError("Expected AttributeError from the fake decomp downstream")


def test_raises_clear_error_when_all_jobs_incomplete(tmp_path):
    """All jobs only have the single init entry -- must raise a clear FileNotFoundError."""
    analysis_folder = str(tmp_path / "analysis")
    job_a = os.path.join(analysis_folder, "optimized", "jobs", "000")
    _write_callback_txt(job_a, [(1, -0.5, [1.0, 2.0])])  # only init entry

    class _FakeDecomp:
        pass

    import pytest
    with pytest.raises(FileNotFoundError, match="No completed job"):
        load_rigorous_result(_FakeDecomp(), analysis_folder)
