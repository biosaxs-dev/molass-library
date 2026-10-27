"""molass-library#335: RunInfo.is_done / wait_until_done mean the same for every kind of run."""
import threading
import time

import pytest

from molass.Rigorous.RunInfo import RunInfo


def _ri():
    return RunInfo(ssd=None, optimizer=None, dsets=None, init_params=None)


class _Proc:
    def __init__(self, returncode=None):
        self.returncode = returncode

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode


def test_fresh_run_without_information_is_not_done():
    ri = _ri()
    assert ri.is_done is False
    assert ri.wait_until_done(timeout=0.1, poll_interval=0.02) is False


def test_synchronous_in_process_run_is_done_once_it_has_a_result():
    ri = _ri()
    ri.in_process_result = object()
    assert ri.is_done is True and ri.wait_until_done(timeout=1) is True


def test_subprocess_run_done_when_the_process_exits():
    ri = _ri()
    ri._subprocess_process = _Proc(None)
    assert ri.is_done is False
    assert ri.wait_until_done(timeout=0.2, poll_interval=0.05) is False
    ri._subprocess_process.returncode = 0
    assert ri.is_done is True and ri.wait_until_done(timeout=1) is True


def test_failed_subprocess_run_counts_as_done():
    ri = _ri()
    ri._subprocess_process = _Proc(1)
    assert ri.is_done is True
    assert ri.live_status()["phase"] == "failed"


def test_async_in_process_run_done_when_the_thread_ends():
    ri = _ri()
    ri._async_thread = threading.Thread(target=time.sleep, args=(0.4,))
    ri._async_thread.start()
    assert ri.is_done is False
    assert ri.wait_until_done(timeout=0.05, poll_interval=0.02) is False
    assert ri.wait_until_done(timeout=5, poll_interval=0.05) is True
    assert ri.is_done is True


def test_async_error_is_raised():
    ri = _ri()
    ri._async_error = ValueError("boom")
    with pytest.raises(RuntimeError, match="Async optimizer failed"):
        ri.wait_until_done(timeout=1)
