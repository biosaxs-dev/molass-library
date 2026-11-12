"""
    Global.Tqdm.py

    ``tqdm`` with progress bars on stdout instead of stderr (molass-library#339):
    stderr is kept for errors.

    The bars can be switched off globally (molass-library#375): ``molass.set_progress(False)``
    or the environment variable ``MOLASS_PROGRESS=0`` (also ``false``, ``off``, ``no``),
    which keeps agent and headless runs readable.

    Default (molass-library#388): the bars are on in a terminal and in a Jupyter kernel, and off when
    the output is not a terminal (a redirected file, CI, a captured subprocess), where a bar cannot
    update in place and only fills the output with one line per update. ``set_progress(True)`` or
    ``MOLASS_PROGRESS=1`` turns them on there as well.
"""
import os
import sys
from tqdm.auto import tqdm as _tqdm
from molass.Global.Streams import stdout_or_null

_OFF_VALUES = ("0", "false", "off", "no")
_ON_VALUES = ("1", "true", "on", "yes")


def _from_environment():
    value = os.environ.get("MOLASS_PROGRESS")
    if value is None:
        return None
    value = value.strip().lower()
    if value in _OFF_VALUES:
        return False
    return True if value in _ON_VALUES else None


# None means "decide from the output stream"
_progress_setting = _from_environment()


def _in_jupyter_kernel():
    ipython = sys.modules.get("IPython")
    shell = ipython.get_ipython() if ipython is not None else None
    return shell is not None and hasattr(shell, "kernel")


def _is_interactive(stream):
    if _in_jupyter_kernel():
        return True
    isatty = getattr(stream, "isatty", None)
    try:
        return bool(isatty()) if isatty is not None else False
    except ValueError:      # closed stream
        return False


def _resolve(stream):
    if _progress_setting is not None:
        return _progress_setting
    return _is_interactive(stream)


def set_progress(enabled):
    """Switch the progress bars of molass on or off (for this process).

    Parameters
    ----------
    enabled : bool or None
        ``False`` silences every progress bar made through :func:`tqdm`, ``True`` shows them even
        when the output is not a terminal, ``None`` restores the default (shown in a terminal or
        a Jupyter kernel only).
    """
    global _progress_setting
    _progress_setting = None if enabled is None else bool(enabled)


def get_progress():
    """Whether progress bars are on: the setting of :func:`set_progress` or ``MOLASS_PROGRESS``
    if there is one, otherwise whether the output is a terminal or a Jupyter kernel."""
    return _resolve(stdout_or_null())


def tqdm(*args, **kwargs):
    """``tqdm.auto.tqdm`` writing to the current ``sys.stdout`` unless ``file`` is given.

    Without a console (``sys.stdout`` is ``None``, e.g. ``pythonw.exe``) the bar is discarded
    instead of raising (molass-library#358). With :func:`set_progress` ``(False)`` the bar is
    disabled (the iterable is still iterated); by default it is disabled when the output is not
    a terminal or a Jupyter kernel (molass-library#388).
    """
    kwargs.setdefault('file', stdout_or_null())
    kwargs.setdefault('disable', not _resolve(kwargs['file']))
    return _tqdm(*args, **kwargs)
