"""Regression test for molass-library#305: get_ready_for_numba() must survive concurrent process starts."""
import os
import subprocess
import sys

CODE = "from molass.PackageUtils.NumbaUtils import get_ready_for_numba; get_ready_for_numba(); print('ok')"


def test_get_ready_for_numba_parallel_processes(tmp_path):
    # Private TEMP for the children: get_ready_for_numba() wipes <TEMP>/numba_cache, which must not
    # hit the cache directory that the running pytest process itself uses (flaky baseline tests).
    env = dict(os.environ, TMP=str(tmp_path), TEMP=str(tmp_path), TMPDIR=str(tmp_path))
    procs = [subprocess.Popen([sys.executable, "-c", CODE], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
             for _ in range(8)]
    results = [p.communicate(timeout=120) + (p.returncode,) for p in procs]
    for out, err, rc in results:
        assert rc == 0, err[-500:]
        assert "ok" in out
