"""
    PackageUtils.NumbaUtils.py
"""
import os
import tempfile

IS_READY_FOR_NUMBA = False

def get_ready_for_numba():
    """
    Prepare the environment for Numba.
    Without this function, Numba will create a cache directory in the package directory
    and it will cause a problem when it is read-only, which is the case when the package
    using numba, e.g., pybaselines, has been installed with the admin privilege.
    (as of numba 0.61.0)
    """
    global IS_READY_FOR_NUMBA
    if IS_READY_FOR_NUMBA:
        return
    
    numba_cache = os.path.join(tempfile.gettempdir(), "numba_cache")
    os.environ['NUMBA_CACHE_DIR'] = numba_cache

    # Do not wipe an existing cache: Numba validates entries against the source
    # file stamp itself, and deleting the shared directory at every start can pull
    # the cache out from under another running process (#305).
    os.makedirs(numba_cache, exist_ok=True)
    IS_READY_FOR_NUMBA = True