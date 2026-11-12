import importlib
import subprocess
import sys

import molass
from molass.Global import Tqdm


def test_progress_can_be_switched_on_and_off(capsys):
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
        molass.set_progress(None)


def test_progress_is_off_by_default_when_output_is_not_a_terminal(capsys):
    molass.set_progress(None)
    assert molass.get_progress() is False                   # captured stdout is not a TTY (#388)
    assert list(Tqdm.tqdm(range(3), mininterval=0)) == [0, 1, 2]
    assert capsys.readouterr().out == ""


def test_environment_variable_switches_progress_from_the_start():
    code = ("import molass; from molass.Global.Tqdm import tqdm; "
            "print(molass.get_progress()); list(tqdm(range(3), mininterval=0))")
    for value, expected in (("0", "False"), ("off", "False"), ("1", "True"), (None, "False")):
        env = {k: v for k, v in __import__("os").environ.items() if k != "MOLASS_PROGRESS"}
        if value is not None:
            env["MOLASS_PROGRESS"] = value
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
        assert result.returncode == 0, result.stderr
        first, rest = result.stdout.splitlines()[0], result.stdout.splitlines()[1:]
        assert first == expected
        assert (rest == []) == (expected == "False")        # no bar at all when switched off
