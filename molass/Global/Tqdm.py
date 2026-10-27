"""
    Global.Tqdm.py

    ``tqdm`` with progress bars on stdout instead of stderr (molass-library#339):
    stderr is kept for errors.
"""
import sys
from tqdm.auto import tqdm as _tqdm


def tqdm(*args, **kwargs):
    """``tqdm.auto.tqdm`` writing to the current ``sys.stdout`` unless ``file`` is given."""
    kwargs.setdefault('file', sys.stdout)
    return _tqdm(*args, **kwargs)
