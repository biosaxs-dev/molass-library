"""
    Global.ArrayBundle.py

    One way to hand named numpy arrays to another process (molass-library#399).

    An :class:`ArrayBundle` is a set of named arrays plus small JSON-able metadata. The same
    bundle travels over three transports, so a worker is written against the bundle and the
    transport can be changed without touching it:

    - **pickle / in memory**: the bundle is picklable (``multiprocessing`` with ``spawn``).
    - **disk**: :meth:`ArrayBundle.save` / :meth:`ArrayBundle.load` -- for a child that outlives
      its parent (e.g. the rigorous optimization) or must be reproducible.
    - **shared memory**: :meth:`ArrayBundle.share` in the owner, :meth:`ArrayBundle.attach` in
      the child -- for a short-lived child of one live session, without copying the data. One
      block per bundle; read-only views unless ``readonly=False`` (a live buffer the child fills
      and the parent polls, e.g. a running Rg curve).

    Shared memory is not a durable store: the owner must keep its :class:`SharedBundle` open for
    as long as children may attach, and close it exactly once.
"""
import json
import os
import re
import sys
import tempfile

import numpy as np
from multiprocessing.shared_memory import SharedMemory

MANIFEST_NAME = "bundle.json"
_FORMAT = 1
_ALIGN = 64
_NAME_PATTERN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")


def _check_name(name):
    if not isinstance(name, str) or _NAME_PATTERN.fullmatch(name) is None:
        raise ValueError(f"invalid array name {name!r}: use letters, digits, '_', '.', '-'")
    return name


def _check_array(name, array):
    array = np.asarray(array)
    if array.dtype.hasobject or array.dtype.fields is not None:
        raise TypeError(f"array {name!r} has dtype {array.dtype}: only plain numeric/bool/string dtypes are supported")
    return array


def _atomic_write(path, write):
    """Call ``write(tmp_path)`` and move the result to ``path`` (no half files for readers)."""
    folder = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(suffix=os.path.splitext(path)[1], dir=folder)
    os.close(fd)
    try:
        write(tmp)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _open_shared_memory(name):
    """Attach to an existing block without letting this process's resource tracker claim it."""
    if sys.version_info >= (3, 13):
        return SharedMemory(name=name, track=False)
    shm = SharedMemory(name=name)
    if os.name == "posix":
        # Python < 3.13 registers an attached block, so the tracker would unlink it when this
        # process exits, under the feet of the owner and of the other children.
        from multiprocessing import resource_tracker
        resource_tracker.unregister(shm._name, "shared_memory")
    return shm


class ArrayBundle:
    """Named numpy arrays plus JSON-able metadata that can be sent to another process.

    Parameters
    ----------
    arrays : dict of str to array-like
        The arrays. Names are used as file names on disk: letters, digits, ``_``, ``.``, ``-``.
        Object and structured dtypes are not supported.
    meta : dict or None, optional
        Small JSON-serializable metadata (e.g. ``{"kind": "XrData"}``).

    Notes
    -----
    Arrays are not copied by the constructor. A bundle returned by :meth:`attach` holds views
    of shared memory: keep it open while its arrays are used and call :meth:`close` (or use it
    as a context manager) when done.
    """

    def __init__(self, arrays, meta=None):
        self._arrays = {_check_name(name): _check_array(name, array) for name, array in arrays.items()}
        self.meta = {} if meta is None else dict(meta)
        json.dumps(self.meta)                    # fail early, not on the way to disk
        self._shm = None

    @classmethod
    def zeros(cls, layout, meta=None):
        """A bundle of zero-filled arrays: ``layout`` maps each name to ``(shape, dtype)``.

        Typically shared writable, as a buffer for a worker to fill (see :meth:`share`).
        """
        return cls({name: np.zeros(shape, dtype=dtype) for name, (shape, dtype) in layout.items()}, meta)

    # -- mapping interface --------------------------------------------------------------
    def __getitem__(self, name):
        return self._arrays[name]

    def __contains__(self, name):
        return name in self._arrays

    def __iter__(self):
        return iter(self._arrays)

    def __len__(self):
        return len(self._arrays)

    def keys(self):
        return self._arrays.keys()

    def __repr__(self):
        items = ", ".join(f"{name}{a.shape}" for name, a in self._arrays.items())
        return f"ArrayBundle({items})"

    # -- pickle ---------------------------------------------------------------------------
    def __getstate__(self):
        return {"arrays": self._arrays, "meta": self.meta}

    def __setstate__(self, state):
        self._arrays = state["arrays"]
        self.meta = state["meta"]
        self._shm = None

    # -- disk -----------------------------------------------------------------------------
    def save(self, folder):
        """Write one ``<name>.npy`` per array and a ``bundle.json`` manifest into ``folder``.

        The manifest is written last, so a folder without it is an unfinished one.
        """
        folder = os.fspath(folder)
        os.makedirs(folder, exist_ok=True)
        for name, array in self._arrays.items():
            _atomic_write(os.path.join(folder, name + ".npy"),
                          lambda tmp, array=array: np.save(tmp, array, allow_pickle=False))
        manifest = {"format": _FORMAT, "names": list(self._arrays), "meta": self.meta}

        def write_manifest(tmp):
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(manifest, fh)

        _atomic_write(os.path.join(folder, MANIFEST_NAME), write_manifest)

    @classmethod
    def load(cls, folder, mmap=False):
        """Read a bundle written by :meth:`save`. With ``mmap=True`` the arrays are read-only memory maps."""
        folder = os.fspath(folder)
        with open(os.path.join(folder, MANIFEST_NAME), encoding="utf-8") as fh:
            manifest = json.load(fh)
        if manifest.get("format") != _FORMAT:
            raise ValueError(f"unsupported bundle format {manifest.get('format')!r} in {folder}")
        mmap_mode = "r" if mmap else None
        arrays = {name: np.load(os.path.join(folder, _check_name(name) + ".npy"), mmap_mode=mmap_mode, allow_pickle=False)
                  for name in manifest["names"]}
        return cls(arrays, manifest["meta"])

    # -- shared memory --------------------------------------------------------------------
    def share(self):
        """Copy the arrays into one shared-memory block and return its owner, a :class:`SharedBundle`."""
        return SharedBundle(self)

    @classmethod
    def attach(cls, spec, readonly=True):
        """Attach to the block described by ``spec`` (``SharedBundle.spec``) and return views of it.

        ``readonly=False`` is for a buffer the child writes into; the owner sees the writes.
        """
        shm = _open_shared_memory(spec["name"])
        arrays = {}
        try:
            for name, shape, dtype, offset in spec["entries"]:
                array = np.ndarray(tuple(shape), dtype=dtype, buffer=shm.buf, offset=offset)
                array.flags.writeable = not readonly
                arrays[name] = array
        except BaseException:
            arrays.clear()
            shm.close()
            raise
        bundle = cls(arrays, spec.get("meta"))
        bundle._shm = shm
        return bundle

    def close(self):
        """Detach from shared memory (no-op for a bundle that is not attached)."""
        shm, self._shm = self._shm, None
        if shm is None:
            return
        self._arrays = {}
        shm.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class SharedBundle:
    """The owner of a shared-memory copy of an :class:`ArrayBundle`; made by :meth:`ArrayBundle.share`.

    Attributes
    ----------
    spec : dict
        Small and picklable: hand this to the child, which calls :meth:`ArrayBundle.attach`.
    bundle : ArrayBundle
        Writable views of the shared block, for the owner to read what a child wrote.

    Use it as a context manager, or call :meth:`close` exactly once: it releases the block.
    Drop the views you took from :attr:`bundle` before that.
    """

    def __init__(self, source):
        entries = []
        offset = 0
        for name, array in source._arrays.items():
            offset = -(-offset // _ALIGN) * _ALIGN
            entries.append([name, list(array.shape), array.dtype.str, offset])
            offset += array.nbytes
        self._shm = SharedMemory(create=True, size=max(offset, 1))
        arrays = {}
        for (name, shape, dtype, start), array in zip(entries, source._arrays.values()):
            view = np.ndarray(tuple(shape), dtype=dtype, buffer=self._shm.buf, offset=start)
            view[...] = array
            arrays[name] = view
        self.spec = {"name": self._shm.name, "entries": entries, "meta": source.meta}
        self.bundle = ArrayBundle(arrays, source.meta)

    def close(self):
        shm, self._shm = self._shm, None
        if shm is None:
            return
        self.bundle._arrays = {}
        try:
            shm.close()
        finally:
            try:
                shm.unlink()
            except FileNotFoundError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
