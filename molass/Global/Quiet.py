"""
    Global.Quiet.py

    Context managers for suppressing verbose output from legacy code.

    The output of the legacy code (peak-boundary traces, tracebacks of exceptions it handles itself,
    mapping results, numerical warnings) is discarded by default; ``debug=True`` shows it.
    ``set_molass_options(quiet=False)`` shows it everywhere (molass-library#83, #398).
"""
import io
import warnings
from contextlib import redirect_stdout, redirect_stderr, contextmanager

_TAIL_LINES = 30


def _is_legacy_noise(record):
    """Warnings the legacy code (and the numerics under it) raise on their own account."""
    from scipy.optimize import OptimizeWarning
    return (issubclass(record.category, (RuntimeWarning, OptimizeWarning))
            or "molass_legacy" in str(record.filename))


@contextmanager
def quiet_legacy(debug=False):
    """Discard the printed output of legacy code unless ``debug`` is True (molass-library#398).

    For the calls that run legacy code which prints peak-boundary traces, tracebacks of handled
    exceptions, mapping results and the like (``upgrade``, ``get_rigorous_initparams``,
    ``load_analysis``, ...). This is the rule ``Decomposition.score()`` always followed.

    stdout and stderr (and with them the legacy ``logging`` output, which goes to the current stdout)
    are discarded, and so are the warnings raised in ``molass_legacy`` and the numerical
    ``RuntimeWarning`` / ``OptimizeWarning`` they cause. Every other warning, e.g. the ``UserWarning``
    of molass itself, is meant for the user: it is shown when the block is left, as if it had been
    raised there (same file and line). If the block raises, the last lines of what was discarded
    are attached to the exception (``add_note``), so that suppressing the output does not hide the cause.
    """
    if debug:
        yield
        return
    captured = io.StringIO()
    records = []
    try:
        with redirect_stdout(captured), redirect_stderr(captured), warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")        # record everything, decide below
            try:
                yield
            except Exception as exc:
                tail = captured.getvalue().rstrip().splitlines()[-_TAIL_LINES:]
                if tail:
                    exc.add_note("Output of the legacy code, suppressed (pass debug=True to see it); last lines:\n"
                                 + "\n".join(tail))
                raise
    finally:
        for record in records:
            if not _is_legacy_noise(record):
                warnings.warn_explicit(record.message, record.category, record.filename, record.lineno,
                                       source=record.source)


@contextmanager
def suppress_if_quiet(debug=False):
    """Context manager that suppresses the legacy output when quiet mode is on (the default).

    Usage::

        from molass.Global.Quiet import suppress_if_quiet

        with suppress_if_quiet():
            # legacy code that prints noise
            ...

    While ``set_molass_options(quiet=True)`` is active (the default) and *debug* is False, the output
    inside the ``with`` block is discarded as described in :func:`quiet_legacy` (warnings meant for the
    user are kept). With ``quiet=False`` or *debug* True the block executes normally.

    Parameters
    ----------
    debug : bool, optional
        If True, never suppress — even when quiet mode is on.
    """
    from molass.Global.Options import get_molass_options
    if debug or not get_molass_options('quiet'):
        yield
        return
    with quiet_legacy():
        yield
