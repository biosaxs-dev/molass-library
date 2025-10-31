import os
from pathlib import Path
import toml

def get_pythonpath_from_pyproject(pyproject_path=None):
    """
    Reads the pythonpath list from [tool.pytest.ini_options] in pyproject.toml.
    Returns a list of absolute paths.
    """
    if pyproject_path is None:
        pyproject_path = Path(__file__).parent.parent / 'pyproject.toml'
    else:
        pyproject_path = Path(pyproject_path)
    if not pyproject_path.exists():
        return []
    try:
        config = toml.load(pyproject_path)
        pythonpath = config.get('tool', {}).get('pytest', {}).get('ini_options', {}).get('pythonpath', [])
        abs_paths = [str((pyproject_path.parent / p).resolve()) for p in pythonpath]
        return abs_paths
    except Exception as e:
        print(f"[WARNING] Could not read pythonpath from pyproject.toml: {e}")
        return []
