# 
import os

def get_version(toml_only=False):
    """
    Retrieve the version of the package from pyproject.toml or importlib.metadata.

    Parameters:
    ------------
    toml_only: bool, optional
        If True, only read the version from pyproject.toml and ensure
        that you are using the local repository. Default is False.
        This is crucial when you are testing in environments you can also
        use the installed package version.
        In fact, while you are testing, it is almost always the case that
        you are updating the local repository (not yet installed version),
        and you will be confused unless you are certain which version you are using.

        If False, read the version from pyproject.toml if it exists,
        otherwise use importlib.metadata.
    """

    pyproject_toml = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'pyproject.toml')
    if os.path.exists(pyproject_toml):
        # If you are using the local repository, read the version from pyproject.toml
        import toml
        pyproject_data = toml.load(pyproject_toml)
        return pyproject_data['project']['version']
    else:
        # Otherwise, use importlib.metadata to get it from the installed package
        assert toml_only is False, "toml_only is not expected in this context"
        import importlib.metadata
        return importlib.metadata.version(__package__)