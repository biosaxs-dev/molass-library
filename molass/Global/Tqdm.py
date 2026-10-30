"""
    Global.Tqdm.py

    ``tqdm`` with progress bars on stdout instead of stderr (molass-library#339):
    stderr is kept for errors.
"""
import sys
from tqdm.auto import tqdm as _tqdm
from molass.Global.Streams import stdout_or_null


def tqdm(*args, **kwargs):
    """``tqdm.auto.tqdm`` writing to the current ``sys.stdout`` unless ``file`` is given.

    Without a console (``sys.stdout`` is ``None``, e.g. ``pythonw.exe``) the bar is discarded
    instead of raising (molass-library#358).
    """
    kwargs.setdefault('file', stdout_or_null())
    return _tqdm(*args, **kwargs)
