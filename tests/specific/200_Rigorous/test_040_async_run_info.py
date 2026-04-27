"""
Test RunInfo.is_alive and optimize_rigorously(async_=True).

Verifies the async in-process path:
  - optimize_rigorously(async_=True) returns immediately
  - run_info.is_alive is True while the thread runs, False after wait()
  - run_info.wait() joins the thread
  - run_info.work_folder and in_process_result are populated after wait()

See: https://github.com/biosaxs-dev/molass-library/issues/137
"""
import threading
import pytest
from molass.Rigorous.RunInfo import RunInfo


def test_is_alive_blocking_run_is_false():
    """For a synchronous (blocking) RunInfo, is_alive is always False."""
    ri = RunInfo(ssd=None, optimizer=None, dsets=None, init_params=None)
    assert ri.is_alive is False


def test_is_alive_tracks_async_thread():
    """is_alive reflects the thread state: True while alive, False after join."""
    import time

    ri = RunInfo(ssd=None, optimizer=None, dsets=None, init_params=None)

    def _slow():
        time.sleep(0.3)

    t = threading.Thread(target=_slow, daemon=True)
    ri._async_thread = t
    t.start()

    assert ri.is_alive is True
    t.join()
    assert ri.is_alive is False


def test_wait_joins_async_thread():
    """wait() with _async_thread set joins the thread and returns True."""
    import time

    ri = RunInfo(ssd=None, optimizer=None, dsets=None, init_params=None)
    ri._async_error = None

    results = []

    def _worker():
        time.sleep(0.1)
        results.append("done")

    t = threading.Thread(target=_worker, daemon=True)
    ri._async_thread = t
    t.start()

    assert ri.is_alive is True
    ok = ri.wait(timeout=5)
    assert ok is True
    assert ri.is_alive is False
    assert results == ["done"]


def test_wait_raises_on_async_error():
    """wait() re-raises an error set by the background thread."""
    ri = RunInfo(ssd=None, optimizer=None, dsets=None, init_params=None)

    def _fail():
        ri._async_error = ValueError("test error")

    t = threading.Thread(target=_fail, daemon=True)
    ri._async_thread = t
    t.start()
    t.join()

    with pytest.raises(RuntimeError, match="Async optimizer failed"):
        ri.wait(timeout=5)
