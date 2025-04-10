# 
import os

def get_version(toml_only=False):
    """
    Retrieve the version of the package from pyproject.toml or importlib.metadata.
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