"""
    Global.Tqdm.py

    ``tqdm`` with progress bars on stdout instead of stderr (molass-library#339):
    stderr is kept for errors.

    The bars can be switched off globally (molass-library#375): ``molass.set_progress(False)``
    or the environment variable ``MOLASS_PROGRESS=0`` (also ``false``, ``off``, ``no``),
    which keeps agent and headless runs readable. The default is on.
"""
import os
import sys
from tqdm.auto import tqdm as _tqdm
from molass.Global.Streams import stdout_or_null

_OFF_VALUES = ("0", "false", "off", "no")
_progress_enabled = os.environ.get("MOLASS_PROGRESS", "1").strip().lower() not in _OFF_VALUES


def set_progress(enabled):
    """Switch the progress bars of molass on or off (for this process).

    Parameters
    ----------
    enabled : bool
        ``False`` silences every progress bar made through :func:`tqdm`.
    """
    global _progress_enabled
    _progress_enabled = bool(enabled)


def get_progress():
    """Whether progress bars are on (``True`` unless switched off by :func:`set_progress`
    or ``MOLASS_PROGRESS=0``)."""
    return _progress_enabled


def tqdm(*args, **kwargs):
    """``tqdm.auto.tqdm`` writing to the current ``sys.stdout`` unless ``file`` is given.

    Without a console (``sys.stdout`` is ``None``, e.g. ``pythonw.exe``) the bar is discarded
    instead of raising (molass-library#358). With :func:`set_progress` ``(False)`` the bar is
    disabled (the iterable is still iterated).
    """
    kwargs.setdefault('file', stdout_or_null())
    kwargs.setdefault('disable', not _progress_enabled)
    return _tqdm(*args, **kwargs)
