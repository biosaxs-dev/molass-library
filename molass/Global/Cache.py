"""
    Global.Cache.py

    Where molass keeps derived data on disk (molass-library#374, #376).

    - The **configured** cache directory is opt-in: ``molass.set_cache_dir(path)`` or the environment
      variable ``MOLASS_CACHE_DIR``. Without it, nothing user-specific is cached (the Rg curve of a
      ``SecSaxsData`` is recomputed in every process).
    - Data derived from the library itself (the reference curves of the Kratky shape library) are
      the same for everyone and are cached in the configured directory if there is one, else in
      the per-user default directory (:func:`default_cache_dir`).

    Every cache file is keyed by a hash of what it was made from, so a stale file is never read.
"""
import os
import tempfile

_cache_dir = os.environ.get("MOLASS_CACHE_DIR") or None


def set_cache_dir(path):
    """Set (or, with ``None``, clear) the cache directory for this process.

    The directory is created when first written to.
    """
    global _cache_dir
    _cache_dir = None if path is None else os.fspath(path)


def get_cache_dir():
    """The configured cache directory, or ``None`` if caching of user data is off."""
    return _cache_dir


def default_cache_dir():
    """The per-user directory for data derived from the library itself."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "molass")


def resolve_cache_dir(create=True):
    """The configured directory if set, else :func:`default_cache_dir`; created if ``create``.

    Returns ``None`` if the directory cannot be created (read-only file system): callers then skip caching.
    """
    path = _cache_dir or default_cache_dir()
    if create:
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            return None
    return path


def atomic_save_npz(path, **arrays):
    """Write an ``.npz`` file atomically (a crashed or concurrent writer never leaves a half file)."""
    import numpy as np
    folder = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(suffix=".npz", dir=folder)
    os.close(fd)
    try:
        np.savez(tmp, **arrays)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
