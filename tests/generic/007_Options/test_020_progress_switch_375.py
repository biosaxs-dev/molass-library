import importlib
import subprocess
import sys

import molass
from molass.Global import Tqdm


def test_progress_is_on_by_default_and_can_be_switched_off(capsys):
    assert molass.get_progress() is True
    try:
        molass.set_progress(False)
        assert molass.get_progress() is False
        assert list(Tqdm.tqdm(range(3))) == [0, 1, 2]       # still iterates
        out = capsys.readouterr()
        assert out.out == "" and out.err == ""
        molass.set_progress(True)
        list(Tqdm.tqdm(range(3), mininterval=0))
        assert capsys.readouterr().out != ""                # the bar is printed to stdout again
    finally:
        molass.set_progress(True)


def test_environment_variable_switches_progress_off_from_the_start():
    code = ("import molass; from molass.Global.Tqdm import tqdm; "
            "print(molass.get_progress()); list(tqdm(range(3), mininterval=0))")
    for value, expected in (("0", "False"), ("off", "False"), ("1", "True")):
        env = dict(__import__("os").environ, MOLASS_PROGRESS=value)
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
        assert result.returncode == 0, result.stderr
        first, rest = result.stdout.splitlines()[0], result.stdout.splitlines()[1:]
        assert first == expected
        assert (rest == []) == (expected == "False")        # no bar at all when switched off
