"""
Tests for RunInfo.reconnect() and optimize_rigorously() idempotency guard.

molass-library#151 — RunInfo.reconnect(analysis_folder)

Covers:
  - reconnect() raises FileNotFoundError when no manifest exists and
    raise_if_not_found=True (default)
  - reconnect() returns None when no manifest exists and
    raise_if_not_found=False
  - reconnect() restores analysis_folder, work_folder from a manifest
  - reconnect() restores subprocess_returncode from manifest
  - _is_subprocess_alive() returns False when manifest has no subprocess_pid
  - idempotency: _active_inprocess sentinel is None after module import
"""
import json
import os
import tempfile
import pytest

from molass.Rigorous.RunInfo import RunInfo
import molass.Rigorous.RunInfo as _run_info_mod


# ── reconnect() ────────────────────────────────────────────────────────────

def test_reconnect_no_manifest_raises():
    """reconnect() raises FileNotFoundError when no manifest exists."""
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(FileNotFoundError, match="RUN_MANIFEST.json"):
            RunInfo.reconnect(tmp)


def test_reconnect_no_manifest_returns_none():
    """reconnect(raise_if_not_found=False) returns None when no manifest."""
    with tempfile.TemporaryDirectory() as tmp:
        result = RunInfo.reconnect(tmp, raise_if_not_found=False)
        assert result is None


def test_reconnect_restores_analysis_folder():
    """reconnect() sets analysis_folder from the manifest folder argument."""
    with tempfile.TemporaryDirectory() as tmp:
        manifest = {
            "schema": "molass.run_manifest/v1",
            "pid": 99999,
            "start_time": "2026-04-30T00:00:00+00:00",
            "folder": tmp,
            "method": "BH",
            "niter": 20,
            "status": "completed",
        }
        with open(os.path.join(tmp, "RUN_MANIFEST.json"), "w") as fh:
            json.dump(manifest, fh)

        ri = RunInfo.reconnect(tmp)
        assert ri.analysis_folder == os.path.abspath(tmp)
        assert ri.optimizer is None
        assert ri.decomposition is None
        assert ri.monitor is None
        assert ri.is_alive is False


def test_reconnect_restores_work_folder_from_manifest():
    """reconnect() picks up work_folder from manifest['work_folder']."""
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = os.path.join(tmp, "optimized", "jobs", "000")
        os.makedirs(work_dir)
        manifest = {
            "schema": "molass.run_manifest/v1",
            "pid": 99999,
            "start_time": "2026-04-30T00:00:00+00:00",
            "folder": tmp,
            "work_folder": work_dir,
            "status": "completed",
        }
        with open(os.path.join(tmp, "RUN_MANIFEST.json"), "w") as fh:
            json.dump(manifest, fh)

        ri = RunInfo.reconnect(tmp)
        assert ri.work_folder == work_dir


def test_reconnect_discovers_work_folder_from_disk():
    """reconnect() falls back to scanning jobs/ when manifest has no work_folder."""
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = os.path.join(tmp, "optimized", "jobs", "000")
        os.makedirs(work_dir)
        manifest = {
            "schema": "molass.run_manifest/v1",
            "pid": 99999,
            "start_time": "2026-04-30T00:00:00+00:00",
            "folder": tmp,
            "status": "completed",
            # no "work_folder" key
        }
        with open(os.path.join(tmp, "RUN_MANIFEST.json"), "w") as fh:
            json.dump(manifest, fh)

        ri = RunInfo.reconnect(tmp)
        assert ri.work_folder == work_dir


def test_reconnect_restores_subprocess_returncode():
    """reconnect() picks up subprocess_returncode from manifest."""
    with tempfile.TemporaryDirectory() as tmp:
        manifest = {
            "schema": "molass.run_manifest/v1",
            "pid": 99999,
            "start_time": "2026-04-30T00:00:00+00:00",
            "folder": tmp,
            "status": "completed",
            "subprocess_returncode": 0,
        }
        with open(os.path.join(tmp, "RUN_MANIFEST.json"), "w") as fh:
            json.dump(manifest, fh)

        ri = RunInfo.reconnect(tmp)
        assert ri.subprocess_returncode == 0


# ── _is_subprocess_alive() ─────────────────────────────────────────────────

def test_is_subprocess_alive_no_pid():
    """_is_subprocess_alive() returns False when manifest has no subprocess_pid."""
    with tempfile.TemporaryDirectory() as tmp:
        manifest = {
            "schema": "molass.run_manifest/v1",
            "pid": 99999,
            "start_time": "2026-04-30T00:00:00+00:00",
            "folder": tmp,
            "status": "running",
            # no subprocess_pid
        }
        with open(os.path.join(tmp, "RUN_MANIFEST.json"), "w") as fh:
            json.dump(manifest, fh)

        ri = RunInfo.reconnect(tmp)
        assert ri._is_subprocess_alive() is False


def test_is_subprocess_alive_completed_status():
    """_is_subprocess_alive() returns False when manifest status is 'completed'."""
    with tempfile.TemporaryDirectory() as tmp:
        manifest = {
            "schema": "molass.run_manifest/v1",
            "pid": 99999,
            "start_time": "2026-04-30T00:00:00+00:00",
            "folder": tmp,
            "status": "completed",
            "subprocess_pid": 12345,  # even with a pid, completed → not alive
        }
        with open(os.path.join(tmp, "RUN_MANIFEST.json"), "w") as fh:
            json.dump(manifest, fh)

        ri = RunInfo.reconnect(tmp)
        assert ri._is_subprocess_alive() is False


def test_is_subprocess_alive_nonexistent_pid():
    """_is_subprocess_alive() returns False for a pid that is not running."""
    with tempfile.TemporaryDirectory() as tmp:
        manifest = {
            "schema": "molass.run_manifest/v1",
            "pid": 99999,
            "start_time": "2026-04-30T00:00:00+00:00",
            "folder": tmp,
            "status": "running",
            "subprocess_pid": 9999999,  # almost certainly not a real pid
        }
        with open(os.path.join(tmp, "RUN_MANIFEST.json"), "w") as fh:
            json.dump(manifest, fh)

        ri = RunInfo.reconnect(tmp)
        # pid 9999999 won't exist on any realistic system
        assert ri._is_subprocess_alive() is False


# ── _active_inprocess sentinel ─────────────────────────────────────────────

def test_active_inprocess_starts_none():
    """_active_inprocess is None when the module is freshly imported."""
    # The module was already imported; check that the sentinel is None
    # (or a dead weak reference — both mean no active run).
    ref = _run_info_mod._active_inprocess
    if ref is None:
        alive = False
    else:
        obj = ref()
        alive = obj is not None and obj.is_alive
    assert alive is False
