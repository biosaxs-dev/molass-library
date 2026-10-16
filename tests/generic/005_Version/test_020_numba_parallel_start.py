"""Regression test for molass-library#305: get_ready_for_numba() must survive concurrent process starts."""
import subprocess
import sys

CODE = "from molass.PackageUtils.NumbaUtils import get_ready_for_numba; get_ready_for_numba(); print('ok')"


def test_get_ready_for_numba_parallel_processes():
    procs = [subprocess.Popen([sys.executable, "-c", CODE], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             for _ in range(8)]
    results = [p.communicate(timeout=120) + (p.returncode,) for p in procs]
    for out, err, rc in results:
        assert rc == 0, err[-500:]
        assert "ok" in out
