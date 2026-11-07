# 
import os

def to_int_tuple(version_string):
    """
    Convert a version string to a tuple of integers for comparison.
    
    Parameters
    ----------
    version_string: str
        A version string in the format 'major.minor.patch'.
        
    Returns
    -------
    tuple: A tuple of integers representing the version.
    """
    return tuple(int(part) for part in version_string.split('.'))

class Version:
    """A class to represent and compare software version strings."""
    def __init__(self, version_string):
        self.version_string = version_string

    def __lt__(self, other):
        return to_int_tuple(self.version_string) < to_int_tuple(other)

    def __ge__(self, other):
        return to_int_tuple(self.version_string) >= to_int_tuple(other)

    def __repr__(self):
        return self.version_string

def _get_version_impl(toml_only, file, package):
    """
    Internal implementation to retrieve the version of the package.
    """
    pyproject_toml = os.path.join(os.path.dirname(os.path.dirname(file)), 'pyproject.toml')
    if os.path.exists(pyproject_toml):
        # If you are using the local repository, read the version from pyproject.toml
        import toml
        pyproject_data = toml.load(pyproject_toml)
        return pyproject_data['project']['version']
    else:
        # Otherwise, use importlib.metadata to get it from the installed package
        assert toml_only is False, "toml_only is not expected in this context"
        import importlib.metadata
        return importlib.metadata.version(package)

def get_version(toml_only=False):
    """
    Retrieve the version of the package from pyproject.toml or importlib.metadata.

    This function prioritizes reading the version from pyproject.toml to ensure
    that the local repository version is used during development or testing.
    If pyproject.toml is not found, it falls back to using importlib.metadata
    to retrieve the version of the installed package.

    Parameters
    ----------
    toml_only: bool, optional
        If True, the function strictly reads the version from pyproject.toml.
        This is crucial to avoid confusion about the version being used,
        which can lead to significant time loss during testing.
        (confusion about the local repository versus the installed).

        If False, the function attempts to read the version from pyproject.toml
        first. If pyproject.toml does not exist, which means you are using the
        installed package, it falls back to using importlib.metadata to retrieve
        this version.

    Returns
    -------
    Version
        An instance of the Version class representing the package version.

    Raises
    ------
    AssertionError:
        If toml_only is True but pyproject.toml is not found. This ensures
        that the function behaves predictably in cases where the local
        repository is not available.

    This docstring was improved in collaboration with GitHub Copilot.
    """
    return Version(_get_version_impl(toml_only, __file__, __package__))

__version__ = str(get_version())


class VersionInfo:
    """Where ``molass.__version__`` comes from and whether it agrees with the installed metadata.

    Attributes
    ----------
    version : str
        The value of ``molass.__version__``.
    source : str
        ``'pyproject'`` when read from the ``pyproject.toml`` next to the package (a source
        checkout / editable install), ``'metadata'`` when read from the installed distribution.
    path : str
        Directory of the imported ``molass`` package.
    metadata_version : str or None
        The version recorded by ``pip`` (``importlib.metadata``); ``None`` if molass is not installed
        as a distribution.
    consistent : bool
        ``True`` unless ``metadata_version`` exists and differs from ``version`` -- with an editable
        install this means the installed metadata is stale (``pip install -e . --no-deps`` refreshes it).
    """

    def __init__(self, version, source, path, metadata_version):
        self.version = version
        self.source = source
        self.path = path
        self.metadata_version = metadata_version
        self.consistent = metadata_version is None or metadata_version == version

    def to_dict(self):
        return dict(version=self.version, source=self.source, path=self.path,
                    metadata_version=self.metadata_version, consistent=self.consistent)

    def __repr__(self):
        lines = [f"molass {self.version} (from {self.source})", f"  path: {self.path}",
                 f"  installed metadata (pip): {self.metadata_version}"]
        if not self.consistent:
            lines.append("  NOTE: the installed metadata differs from the code version; with an editable install "
                         "run `pip install -e <repo> --no-deps` to refresh it (results record the code version).")
        return "\n".join(lines)


def _version_info_impl(file, package, version):
    import importlib.metadata
    pkg_dir = os.path.dirname(file)
    source = 'pyproject' if os.path.exists(os.path.join(os.path.dirname(pkg_dir), 'pyproject.toml')) else 'metadata'
    try:
        metadata_version = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        metadata_version = None
    return VersionInfo(version, source, pkg_dir, metadata_version)


def version_info():
    """Where the molass version comes from, and whether it is consistent (molass-library#378).

    ``molass.__version__`` reads ``pyproject.toml`` in a source checkout, while ``pip list`` shows the
    metadata recorded at install time; with an editable install the two can differ, and result files
    record ``__version__``. This function shows both.

    Returns
    -------
    VersionInfo
        Prints as a short readable block; see :class:`VersionInfo` for the attributes.

    Examples
    --------
    >>> import molass
    >>> molass.version_info()
    """
    return _version_info_impl(__file__, __package__, __version__)


def set_progress(enabled):
    """Switch the progress bars of molass on or off for this process (molass-library#375).

    The environment variable ``MOLASS_PROGRESS=0`` does the same from the start. Default: on.
    """
    from molass.Global.Tqdm import set_progress as _set_progress
    _set_progress(enabled)


def get_progress():
    """Whether molass progress bars are on (see :func:`set_progress`)."""
    from molass.Global.Tqdm import get_progress as _get_progress
    return _get_progress()


def set_cache_dir(path):
    """Set the directory where molass caches derived data (molass-library#376); ``None`` switches it off.

    Opt-in: with a directory set, ``SecSaxsData.get_rg_curve()`` stores and reloads the per-frame Rg
    curve instead of refitting every frame in every process (15-50 s). The environment variable
    ``MOLASS_CACHE_DIR`` does the same from the start. Files are keyed by a hash of the data and the
    trimming, so a changed input is never served from a stale file.
    """
    from molass.Global.Cache import set_cache_dir as _set_cache_dir
    _set_cache_dir(path)


def get_cache_dir():
    """The configured cache directory, or ``None`` (see :func:`set_cache_dir`)."""
    from molass.Global.Cache import get_cache_dir as _get_cache_dir
    return _get_cache_dir()

def requires(version):
    """
    Assert that the installed molass version meets a minimum requirement.

    Use this at the top of notebooks or tutorial tests instead of a raw
    ``assert get_version() >= '...'`` to make the version dependency
    explicit and easily discoverable.

    Parameters
    ----------
    version : str
        Minimum required version string, e.g. ``'0.8.5'``.

    Raises
    ------
    ImportError
        If the installed molass version is older than *version*.

    Examples
    --------
    >>> from molass import requires
    >>> requires('0.8.5')
    """
    current = get_version()
    if not (current >= version):
        raise ImportError(
            f"This code requires molass >= {version}, but {current} is installed. "
            f"Please upgrade: pip install --upgrade molass"
        )

def context_path():
    """Return the absolute path to CONTEXT.md, the AI-assistant context file
    shipped inside this package.

    Unlike a source repository's ``.github/copilot-instructions.md``, this
    file ships with the installed package itself, so it stays current for
    whichever version is installed -- useful when working in a project that
    only depends on ``molass`` rather than developing it.

    Returns
    -------
    str

    Examples
    --------
    >>> import molass
    >>> molass.context_path()
    '.../site-packages/molass/CONTEXT.md'
    """
    return os.path.join(os.path.dirname(__file__), "CONTEXT.md")

def print_context():
    """Print CONTEXT.md (see :func:`context_path`) to stdout."""
    with open(context_path(), encoding="utf-8") as fh:
        text = fh.read()
    try:
        print(text)
    except UnicodeEncodeError:
        # e.g. cp932 consoles on Japanese Windows can't encode en-dashes/arrows;
        # fall back to a safe, lossy print rather than crashing.
        import sys
        print(text.encode(sys.stdout.encoding or "ascii", errors="replace").decode(sys.stdout.encoding or "ascii"))

def load_analysis(analysis_folder, jobid='best', rgcurve=None, in_folder=None, light=False):
    """Open an analysis folder in one call: best result, score value, jobs, rejected iterations, recipe.

    Lazy wrapper of :func:`molass.Rigorous.AnalysisFolder.load_analysis`; see there for the details.
    ``light=True`` skips the rebuild of the decomposition (see :func:`analysis_status`).

    Examples
    --------
    >>> import molass
    >>> info = molass.load_analysis("analysis-001")
    >>> print(info)
    >>> info.result.plot_components()
    """
    from molass.Rigorous.AnalysisFolder import load_analysis as _load_analysis
    return _load_analysis(analysis_folder, jobid=jobid, rgcurve=rgcurve, in_folder=in_folder, light=light)

def analysis_status(analysis_folder):
    """The light status of an analysis folder, read from its files in seconds (no decomposition rebuild).

    Lazy wrapper of :func:`molass.Rigorous.AnalysisStatus.analysis_status`; see there for the details.
    Meant for polling a running analysis and for surveying many folders; ``status.diagnose()`` lists
    the warnings (stalled, at the starting point, many non-finite iterations, former bounds, on a bound).

    Examples
    --------
    >>> import molass
    >>> status = molass.analysis_status("analysis-001")
    >>> print(status)
    >>> status.is_active, status.fv, status.diagnose()
    """
    from molass.Rigorous.AnalysisStatus import analysis_status as _analysis_status
    return _analysis_status(analysis_folder)

from molass.LowRank.AlignDecompositions import align_decompositions  # noqa: E402
from molass.Dev.ReloadAll import reload_all  # noqa: E402
from molass.PackageUtils.EnvironmentReport import environment_report  # noqa: E402

# informational log messages go to stdout, not stderr (molass-library#339)
from molass.Global.LogSetup import install_stdout_logging  # noqa: E402
install_stdout_logging()