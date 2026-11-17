"""Progress of a running subprocess in the manifest and the status views (molass-library#397).
Synthetic folders only, no optimizer is run."""
import json
import os
import threading
import time
from datetime import datetime, timedelta

import pytest

from molass.Rigorous.CurrentStateUtils import seconds_per_callback
from molass.Rigorous.RunRegistry import (
    MANIFEST_NAME, refresh_run_manifest, start_manifest_watcher, update_run_manifest, write_run_manifest,
)

BASE = datetime(2026, 1, 1, 12, 0, 0)


def _write_job(folder, jobid, offsets, fv=-1.0):
    """A callback.txt with one entry per offset (seconds after BASE)."""
    job_dir = os.path.join(folder, "optimized", "jobs", jobid)
    os.makedirs(job_dir, exist_ok=True)
    with open(os.path.join(job_dir, "callback.txt"), "w") as f:
        for i, offset in enumerate(offsets):
            f.write(f"t={(BASE + timedelta(seconds=offset)).strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("x=\n[ 1.0]\n")
            f.write(f"f={fv - 0.01 * i}\n")
            f.write(f"a={'True' if i else 'False'}\n")
            f.write(f"c={i * 1000}\n")
    return job_dir


def _running_folder(tmp_path):
    folder = str(tmp_path)
    write_run_manifest(folder, status="running", phase="optimizer_ready", subprocess_pid=os.getpid())
    return folder


def test_seconds_per_callback_is_the_recent_mean(tmp_path):
    folder = str(tmp_path)
    _write_job(folder, "000", [0, 10, 20, 40])
    assert seconds_per_callback(folder) == pytest.approx(40 / 3)
    assert seconds_per_callback(folder, recent=2) == pytest.approx(15.0)      # (40 - 10) / 2


def test_the_rate_is_that_of_the_newest_job_with_two_entries(tmp_path):
    folder = str(tmp_path)
    _write_job(folder, "000", [0, 100, 200])
    _write_job(folder, "001", [300])                       # just started: only its start entry
    assert seconds_per_callback(folder) == pytest.approx(100.0)
    _write_job(folder, "001", [300, 305, 310])
    assert seconds_per_callback(folder) == pytest.approx(5.0)


def test_there_is_no_rate_before_two_timestamps(tmp_path):
    folder = str(tmp_path)
    assert seconds_per_callback(folder) is None
    _write_job(folder, "000", [0])
    assert seconds_per_callback(folder) is None


def test_refresh_stores_the_progress_numbers_in_the_manifest(tmp_path):
    folder = _running_folder(tmp_path)
    _write_job(folder, "000", [0, 30, 60, 90])
    manifest = refresh_run_manifest(folder)
    assert manifest["status"] == "running" and manifest["phase"] == "optimizing"
    assert manifest["n_callbacks"] == 4
    assert manifest["best_fv"] == pytest.approx(-1.03)
    assert manifest["seconds_per_callback"] == pytest.approx(30.0)
    assert manifest["last_callback_time"]
    on_disk = json.load(open(os.path.join(folder, MANIFEST_NAME)))
    assert on_disk["seconds_per_callback"] == pytest.approx(30.0)


def _wait_for(predicate, timeout=15.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        value = predicate()
        if value:
            return value
        time.sleep(0.02)
    return None


def _raw_manifest(folder):
    try:
        with open(os.path.join(folder, MANIFEST_NAME)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def test_the_watcher_keeps_the_manifest_file_current_while_the_run_goes_on(tmp_path):
    folder = _running_folder(tmp_path)
    assert _raw_manifest(folder).get("n_callbacks") is None           # what an observer saw: nothing
    watcher = start_manifest_watcher(folder, interval_s=0.05)
    try:
        _write_job(folder, "000", [0, 20, 40])
        assert _wait_for(lambda: _raw_manifest(folder).get("n_callbacks") == 3), "the watcher did not write"
        _write_job(folder, "000", [0, 20, 40, 60, 80])
        assert _wait_for(lambda: _raw_manifest(folder).get("n_callbacks") == 5)
        raw = _raw_manifest(folder)
        assert raw["seconds_per_callback"] == pytest.approx(20.0) and raw["phase"] == "optimizing"
    finally:
        watcher.stop()
    assert not watcher._thread.is_alive()


def test_the_watcher_survives_a_folder_that_is_not_ready(tmp_path):
    watcher = start_manifest_watcher(str(tmp_path / "missing"), interval_s=0.02)
    time.sleep(0.2)
    assert watcher._thread.is_alive()
    watcher.stop()


def test_concurrent_manifest_updates_never_tear_the_file(tmp_path):
    folder = _running_folder(tmp_path)
    write_run_manifest(folder, status="running", keep_me="yes")
    stop = threading.Event()
    torn = []

    def writer(tag):
        n = 0
        while not stop.is_set():
            update_run_manifest(folder, **{f"writer_{tag}": n})
            n += 1

    def reader():
        while not stop.is_set():
            path = os.path.join(folder, MANIFEST_NAME)
            try:
                with open(path) as f:
                    json.load(f)
            except ValueError as exc:
                torn.append(exc)
            except OSError:
                pass

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(2)] + [threading.Thread(target=reader)]
    for t in threads:
        t.start()
    time.sleep(1.5)
    stop.set()
    for t in threads:
        t.join()
    assert torn == []
    assert _raw_manifest(folder)["keep_me"] == "yes"
    assert [name for name in os.listdir(folder) if name.endswith(".tmp")] == []


def test_the_status_of_a_running_analysis_shows_progress_and_rate(tmp_path):
    import molass
    folder = _running_folder(tmp_path)
    _write_job(folder, "000", [0, 30, 60])
    status = molass.analysis_status(folder)
    assert status.is_active
    assert status.seconds_per_callback == pytest.approx(30.0)
    assert status.seconds_since_callback > 0
    text = status.summary()
    assert "progress: 3 callbacks" in text and "30 s per callback" in text and "last callback" in text


def test_a_finished_analysis_has_no_progress_line(tmp_path):
    import molass
    folder = str(tmp_path)
    write_run_manifest(folder, status="completed", phase="finished")
    _write_job(folder, "000", [0, 30, 60])
    assert "progress:" not in molass.analysis_status(folder).summary()


def test_live_status_reports_the_rate(tmp_path):
    from molass.Rigorous.RunInfo import RunInfo
    folder = _running_folder(tmp_path)
    _write_job(folder, "000", [0, 12, 24])
    info = RunInfo(ssd=None, optimizer=None, dsets=None, init_params=None)
    info.analysis_folder = folder
    status = info.live_status()
    assert status["seconds_per_callback"] == pytest.approx(12.0)
    assert status["seconds_since_callback"] > 0
    assert status["n_callbacks"] == 3
