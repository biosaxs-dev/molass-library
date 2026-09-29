"""
Dev.ReloadAll.py

Development-time helper for iterating on molass-library source against a live
notebook kernel (editable install). Manually reloading every affected module in the
right dependency order is a recurring source of confusing ImportError/AttributeError
failures whenever a change spans more than one file -- see molass-library issue #283.
"""
import sys
import importlib

DEFAULT_PREFIX = 'molass'
MAX_PASSES = 3


def reload_all(prefix=DEFAULT_PREFIX, verbose=False):
    """
    Reload every already-imported module under the given package prefix.

    Repeatedly walks ``sys.modules`` and reloads each matching module, for multiple
    passes -- this sidesteps having to know the exact dependency order by hand:
    module-level cross-references (``from X import Y`` at the top of a file) only
    pick up a freshly-reloaded ``Y`` once ``X`` itself is reloaded *after* ``Y``, so a
    single pass in an arbitrary order can leave some modules stale. A few full passes
    converge regardless of starting order, since each pass re-executes every
    module's top-level imports against whatever is currently in ``sys.modules``.

    Does NOT fix already-constructed instances that cached a reference to a
    pre-reload class (e.g. an object whose ``__class__`` predates the reload) --
    those still need to be explicitly rebuilt/invalidated by the caller.

    Parameters
    ----------
    prefix : str, optional
        Only modules named exactly this, or starting with ``prefix + '.'``, are
        reloaded. Default ``'molass'``.
    verbose : bool, optional
        If True, print each module name as it's reloaded, and any errors still
        outstanding after the final pass. Default False.

    Returns
    -------
    int
        Number of modules successfully reloaded on the last pass.

    Examples
    --------
    >>> import molass
    >>> molass.reload_all()   # after editing molass-library source in-place
    """
    names = [n for n in list(sys.modules.keys())
              if n == prefix or n.startswith(prefix + '.')]

    reloaded = 0
    errors = {}
    for _pass in range(MAX_PASSES):
        reloaded = 0
        errors = {}
        for name in names:
            module = sys.modules.get(name)
            if module is None:
                continue
            try:
                importlib.reload(module)
                reloaded += 1
                if verbose:
                    print(f"reloaded {name}")
            except Exception as exc:
                errors[name] = exc
        if not errors:
            break

    if verbose and errors:
        print(f"reload_all: {len(errors)} module(s) still failing after {MAX_PASSES} passes:")
        for name, exc in errors.items():
            print(f"  {name}: {exc!r}")

    return reloaded
