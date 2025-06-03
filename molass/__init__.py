# 
import os

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

    Parameters:
    ------------
    toml_only: bool, optional
        If True, the function strictly reads the version from pyproject.toml.
        This is crucial to avoid confusion about the version being used,
        which can lead to significant time loss during testing.
        (confusion about the local repository versus the installed).

        If False, the function attempts to read the version from pyproject.toml
        first. If pyproject.toml does not exist, which means you are using the
        installed package, it falls back to using importlib.metadata to retrieve
        this version.

    Raises:
    -------
    AssertionError:
        If toml_only is True but pyproject.toml is not found. This ensures
        that the function behaves predictably in cases where the local
        repository is not available.

    This docstring was improved in collaboration with GitHub Copilot.
    """
    return  _get_version_impl(toml_only, __file__, __package__)