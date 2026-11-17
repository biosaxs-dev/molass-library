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


_TAIL_LINES = 30


@contextmanager
def quiet_legacy(debug=False):
    """Discard the printed output of legacy code unless ``debug`` is True (molass-library#398).

    The rule ``Decomposition.score()`` always followed, for the calls that run legacy code which prints
    peak-boundary traces, tracebacks of handled exceptions, mapping results and the like
    (``upgrade``, ``get_rigorous_initparams``, ``load_analysis``, ...). Unlike :func:`suppress_if_quiet`
    it does not depend on ``set_molass_options(quiet=...)``.

    stdout and stderr (and with them the legacy ``logging`` output, which goes to the current stdout)
    are discarded, and so are the warnings raised in ``molass_legacy`` and the numerical ``RuntimeWarning``
    / ``OptimizeWarning`` they cause. ``UserWarning`` s of molass itself are kept: they are meant for the
    user. If the block raises, the last lines of what was discarded are attached to the exception
    (``add_note``), so that suppressing the output does not hide the cause.
    """
    if debug:
        yield
        return
    from scipy.optimize import OptimizeWarning
    captured = io.StringIO()
    with redirect_stdout(captured), redirect_stderr(captured), warnings.catch_warnings():
        warnings.filterwarnings("ignore", module=r"molass_legacy")
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        warnings.filterwarnings("ignore", category=OptimizeWarning)
        try:
            yield
        except Exception as exc:
            tail = captured.getvalue().rstrip().splitlines()[-_TAIL_LINES:]
            if tail:
                exc.add_note("Output of the legacy code, suppressed (pass debug=True to see it); last lines:\n"
                             + "\n".join(tail))
            raise
