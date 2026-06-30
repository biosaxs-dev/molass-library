"""
    Global.Quiet.py

    Context manager for suppressing verbose output from legacy code.
"""
import io
import warnings
from contextlib import redirect_stdout, redirect_stderr, contextmanager


@contextmanager
def suppress_if_quiet(debug=False):
    """Context manager that suppresses stdout, stderr, and warnings when quiet mode is on.

    Usage::

        from molass.Global.Quiet import suppress_if_quiet

        with suppress_if_quiet():
            # legacy code that prints noise
            ...

    When ``set_molass_options(quiet=True)`` is active and *debug* is False,
    all output inside the ``with`` block is discarded.  When ``quiet=False``
    (default) or *debug* is True, the block executes normally.

    Parameters
    ----------
    debug : bool, optional
        If True, never suppress — even when quiet mode is on.
    """
    from molass.Global.Options import get_molass_options
    if debug or not get_molass_options('quiet'):
        yield
        return

    with redirect_stdout(io.StringIO()), \
         redirect_stderr(io.StringIO()), \
         warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield
