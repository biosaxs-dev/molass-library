"""
Test that run_info.wait() on an async in-process run emits a UserWarning
redirecting the user to load_first().

See: https://github.com/biosaxs-dev/molass-library/issues/155
"""
import threading
import warnings
import pytest
from unittest.mock import MagicMock


def _make_fake_run_info():
    """Return a RunInfo with a completed (no-op) async thread."""
    from molass.Rigorous.RunInfo import RunInfo
    run_info = MagicMock(spec=RunInfo)
    # Give it a real, already-finished daemon thread
    t = threading.Thread(target=lambda: None, daemon=True)
    t.start()
    t.join()
    run_info._async_thread = t
    run_info._async_error = None
    # Wire wait() to the real implementation
    run_info.wait = lambda **kw: RunInfo.wait(run_info, **kw)
    return run_info


def test_wait_emits_userwarning_for_async_in_process():
    """run_info.wait() must emit a UserWarning for async in-process runs."""
    run_info = _make_fake_run_info()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        run_info.wait()

    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 1, "Expected exactly one UserWarning from wait()"
    msg = str(user_warnings[0].message)
    assert "load_first" in msg, f"Warning should mention load_first(), got: {msg}"
