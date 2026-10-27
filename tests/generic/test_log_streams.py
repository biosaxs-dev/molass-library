"""molass-library#339: informational output goes to stdout, stderr is kept for errors."""
import subprocess
import sys


def _run(code):
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300)


def test_library_warnings_go_to_stdout_not_stderr():
    r = _run("import molass, logging\n"
             "logging.getLogger('molass_legacy.Trimming.FlangeLimit').warning('zeros replaced')\n"
             "logging.getLogger('molass.Anything').warning('another')\n")
    assert r.returncode == 0
    assert "zeros replaced" in r.stdout and "another" in r.stdout
    assert "zeros replaced" not in r.stderr and "another" not in r.stderr


def test_application_logging_is_not_duplicated():
    r = _run("import molass, logging, sys\n"
             "logging.basicConfig(stream=sys.stderr, format='APP:%(message)s')\n"
             "logging.getLogger('molass_legacy.x').warning('hello')\n")
    assert r.stderr.count("APP:hello") == 1
    assert "hello" not in r.stdout.replace("APP:hello", "")


def test_info_messages_stay_hidden():
    r = _run("import molass, logging\n"
             "logging.getLogger('molass_legacy.x').info('chatty')\n")
    assert "chatty" not in r.stdout + r.stderr


def test_quiet_mode_silences_the_library_log_output():
    r = _run("import molass, logging\n"
             "from molass.Global.Quiet import suppress_if_quiet\n"
             "from molass.Global.Options import set_molass_options\n"
             "set_molass_options(quiet=True)\n"
             "with suppress_if_quiet():\n"
             "    logging.getLogger('molass_legacy.x').warning('noise')\n")
    assert "noise" not in r.stdout + r.stderr


def test_progress_bars_are_written_to_stdout():
    r = _run("from molass.Global.Tqdm import tqdm\n"
             "for _ in tqdm(range(3), desc='progress-check'):\n"
             "    pass\n")
    assert "progress-check" in r.stdout and r.stderr == ""
