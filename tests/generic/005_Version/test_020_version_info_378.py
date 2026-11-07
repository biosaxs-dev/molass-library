import importlib.metadata
import os

import molass
from molass import _version_info_impl


def test_version_info_of_this_checkout():
    info = molass.version_info()
    assert info.version == molass.__version__
    assert info.source == 'pyproject'                       # the tests run from a source checkout
    assert os.path.isdir(info.path)
    assert set(info.to_dict()) == {'version', 'source', 'path', 'metadata_version', 'consistent'}
    assert "molass" in repr(info) and info.version in repr(info)


def test_version_info_reports_stale_metadata(tmp_path, monkeypatch):
    package_dir = tmp_path / "molass"
    package_dir.mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nversion = '9.9.9'\n")
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "9.9.8")
    info = _version_info_impl(str(package_dir / "__init__.py"), "molass", "9.9.9")
    assert info.source == 'pyproject' and info.metadata_version == "9.9.8" and not info.consistent
    assert "pip install -e" in repr(info)                   # says how to refresh the stale metadata


def test_version_info_from_installed_metadata(tmp_path, monkeypatch):
    package_dir = tmp_path / "site-packages" / "molass"
    package_dir.mkdir(parents=True)
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "1.2.3")
    info = _version_info_impl(str(package_dir / "__init__.py"), "molass", "1.2.3")
    assert info.source == 'metadata' and info.consistent


def test_version_info_without_a_distribution(tmp_path, monkeypatch):
    def not_installed(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", not_installed)
    info = _version_info_impl(str(tmp_path / "molass" / "__init__.py"), "molass", "1.0.0")
    assert info.metadata_version is None and info.consistent
