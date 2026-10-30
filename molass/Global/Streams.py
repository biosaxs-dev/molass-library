"""
    Global.Streams.py

    ``sys.stdout`` / ``sys.stderr`` are ``None`` when a program runs under ``pythonw.exe`` (no console), in an
    embedded interpreter or as a service. Library code that writes progress bars or log messages must not fail
    there (molass-library#358).
"""
import os
import sys

_null_stream = None


def null_stream():
    """A shared writable stream that discards everything."""
    global _null_stream
    if _null_stream is None:
        _null_stream = open(os.devnull, "w", encoding="utf-8")
    return _null_stream


def stdout_or_null():
    """The current ``sys.stdout``, or a stream discarding the output if there is none."""
    return sys.stdout if sys.stdout is not None else null_stream()
