import time

import numpy as np
import pytest

import molass
from molass.Testing import Species, simulate_ssd


def _ssd(seed=1, frames=60):
    species = [Species(amp=1.0, center=frames // 2, sigma=5, mass=2.0, rg=36.0)]
    return simulate_ssd(species, noise=1.0, seed=seed, xr_frames=np.arange(frames))


def test_the_job_gives_the_same_curve_as_the_in_process_computation():
    ssd = _ssd()
    expected = _ssd().get_rg_curve()
    with ssd.start_rg_curve_process() as job:
        curve = job.result(timeout=300)
        n_done, buffer = job.progress()
        assert job.done and job.poll() == ("done", curve)
    assert n_done == job.n_frames == len(expected.frames)
    np.testing.assert_array_equal(curve.frames, expected.frames)
    np.testing.assert_allclose(curve.rgs, expected.rgs, equal_nan=True)
    np.testing.assert_allclose(curve.scores, expected.scores)
    np.testing.assert_allclose(curve.i0s, expected.i0s, equal_nan=True)
    assert ssd.get_rg_curve() is curve                     # stored: later calls are free
    assert ssd.start_rg_curve_process().result() is curve  # known curve: no new process


def test_the_job_fills_the_cache_dir(tmp_path):
    try:
        molass.set_cache_dir(tmp_path)
        _ssd().start_rg_curve_process().result(timeout=300)
        assert len(list(tmp_path.glob("rgcurve-*.npz"))) == 1
        job = _ssd().start_rg_curve_process()              # a new object with the same data: from the cache
        assert job.done
    finally:
        molass.set_cache_dir(None)


def test_progress_is_live_and_cancel_releases_the_job():
    job = _ssd(frames=600).start_rg_curve_process()
    try:
        t0 = time.monotonic()
        while job.progress()[0] == 0 and job.poll() is None and time.monotonic() - t0 < 120:
            time.sleep(0.1)
        n_done, buffer = job.progress()
        assert 0 < n_done <= job.n_frames and buffer[:n_done].any()
    finally:
        job.cancel()
    assert job.poll() == ("cancelled", None) and job.done
    with pytest.raises(RuntimeError):
        job.result()


def test_a_child_that_dies_is_reported():
    job = _ssd(frames=600).start_rg_curve_process()
    try:
        job._process.terminate()
        t0 = time.monotonic()
        outcome = job.poll()
        while outcome is None and time.monotonic() - t0 < 60:
            time.sleep(0.1)
            outcome = job.poll()
        assert outcome[0] == "error" and "exited unexpectedly" in outcome[1]
    finally:
        job.close()
