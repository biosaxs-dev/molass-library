"""Regression test for molass-library#305: get_ready_for_numba() must survive concurrent process starts."""
import os
import subprocess
import sys

CODE = "from molass.PackageUtils.NumbaUtils import get_ready_for_numba; get_ready_for_numba(); print('ok')"


def test_get_ready_for_numba_parallel_processes(tmp_path):
    env = dict(os.environ, TMP=str(tmp_path), TEMP=str(tmp_path), TMPDIR=str(tmp_path))
    procs = [subprocess.Popen([sys.executable, "-c", CODE], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
             for _ in range(8)]
    results = [p.communicate(timeout=120) + (p.returncode,) for p in procs]
    for out, err, rc in results:
        assert rc == 0, err[-500:]
        assert "ok" in out


def test_get_ready_for_numba_keeps_existing_cache(tmp_path):
    cache = tmp_path / "numba_cache"
    cache.mkdir()
    marker = cache / "marker.nbi"
    marker.write_text("cache of another running process")
    env = dict(os.environ, TMP=str(tmp_path), TEMP=str(tmp_path), TMPDIR=str(tmp_path))
    r = subprocess.run([sys.executable, "-c", CODE], capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 0, r.stderr[-500:]
    assert marker.exists()
