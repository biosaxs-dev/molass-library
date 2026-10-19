"""
    PackageUtils.EnvironmentReport.py

    Environment facts that decide whether two machines can be expected to give
    bit-identical numerical results (molass-library#302; the BLAS kernel is what
    differed between machines in #293).
"""
import os
import platform
import sys

# environment variables that change numerical kernels / caches and are worth reporting when set
_RELEVANT_ENV_VARS = (
    "OPENBLAS_CORETYPE", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
    "NPY_DISABLE_CPU_FEATURES", "NUMBA_CACHE_DIR", "NUMBA_DISABLE_JIT",
)
_PACKAGES = ("numpy", "scipy", "scikit-learn", "pandas", "numba", "pybaselines", "ruptures",
             "molass_legacy", "molass_data")


def _package_version(name):
    from importlib.metadata import version, PackageNotFoundError
    for candidate in (name, name.replace("_", "-")):
        try:
            return version(candidate)
        except PackageNotFoundError:
            continue
    return None


def environment_report():
    """Return the environment facts relevant to reproducing numerical results.

    Returns
    -------
    dict
        ``python``, ``platform``, ``machine``, ``processor``, ``molass`` and
        ``packages`` (version or ``None`` if not installed), ``blas`` (one entry per
        loaded BLAS/OpenMP library with ``internal_api``, ``version``, ``architecture`` --
        the CPU kernel it selected -- and ``num_threads``), and ``env`` (the relevant
        environment variables that are set, e.g. ``OPENBLAS_CORETYPE``).

    Notes
    -----
    Different CPU/BLAS kernels can give slightly different floating-point results, which
    some fits (e.g. the single-peak XR/UV mapping used for trimming) amplify into
    different trimming slices; see :meth:`molass.DataObjects.SecSaxsData.trimmed_copy`.
    Compare the reports of two machines when their results differ.

    Examples
    --------
    >>> import molass
    >>> report = molass.environment_report()
    >>> report["blas"][0]["architecture"]    # the OpenBLAS CPU kernel in use, e.g. 'Haswell'
    'SkylakeX'
    """
    import molass
    try:
        from threadpoolctl import threadpool_info
        blas = [{k: d.get(k) for k in ("internal_api", "version", "architecture", "num_threads")}
                for d in threadpool_info()]
    except Exception:
        blas = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "molass": molass.__version__,
        "packages": {name: _package_version(name) for name in _PACKAGES},
        "blas": blas,
        "env": {k: os.environ[k] for k in _RELEVANT_ENV_VARS if k in os.environ},
    }
