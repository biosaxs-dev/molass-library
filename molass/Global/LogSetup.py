"""
    Global.LogSetup.py

    Keeps informational output of the library on stdout and stderr for errors (molass-library#339).

    Without a configured handler the ``logging`` module prints WARNING and above of every logger
    to stderr ("last resort"), which, e.g. under PowerShell with ``2>&1``, turns the legacy code's
    warnings into ``NativeCommandError`` and a failing exit code although the run succeeded.
"""
import logging
import sys


class _StdoutHandler(logging.StreamHandler):
    """Writes to the *current* ``sys.stdout`` (so that ``set_molass_options(quiet=True)`` and
    redirections apply) and stays silent once the application configures its own logging."""

    def __init__(self):
        super().__init__(sys.stdout)

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, value):
        pass

    def emit(self, record):
        if sys.stdout is None:                 # no console (pythonw.exe): nowhere to write (molass-library#358)
            return
        if logging.getLogger().handlers:       # the application configured logging: let it decide
            return
        super().emit(record)


def install_stdout_logging():
    """Attach the stdout handler to the ``molass`` and ``molass_legacy`` loggers (idempotent)."""
    for name in ('molass', 'molass_legacy'):
        logger = logging.getLogger(name)
        if not any(isinstance(h, _StdoutHandler) for h in logger.handlers):
            handler = _StdoutHandler()
            handler.setLevel(logging.WARNING)
            handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(handler)
