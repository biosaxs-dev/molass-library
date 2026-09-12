"""
    test DataUtils.DropboxSync

    Pure-logic tests only -- no live Dropbox account is required or used.
    (An account-specific end-to-end sync was verified manually against a
    real folder; see molass-researcher's DATA_SOURCES.md for that record.)
"""
import json
from types import SimpleNamespace

from molass.DataUtils.DropboxSync import _folder_signature, load_credentials


def _fake_entry(rel_path, content_hash, size):
    return SimpleNamespace(path_display=f"/root/{rel_path}", content_hash=content_hash, size=size)


def test_010_folder_signature_deterministic_and_order_independent():
    entries = [
        _fake_entry("a.dat", "hash_a", 10),
        _fake_entry("sub/b.dat", "hash_b", 20),
    ]
    sig1 = _folder_signature(entries, "/root")
    sig2 = _folder_signature(list(reversed(entries)), "/root")
    assert sig1 == sig2, "signature should not depend on entry order"


def test_020_folder_signature_changes_with_content():
    entries = [_fake_entry("a.dat", "hash_a", 10)]
    changed = [_fake_entry("a.dat", "hash_a_v2", 10)]
    assert _folder_signature(entries, "/root") != _folder_signature(changed, "/root")


def test_030_folder_signature_ignores_folder_entries():
    file_entry = _fake_entry("a.dat", "hash_a", 10)
    folder_entry = SimpleNamespace(path_display="/root/sub")  # no content_hash attribute
    with_folder = _folder_signature([file_entry, folder_entry], "/root")
    without_folder = _folder_signature([file_entry], "/root")
    assert with_folder == without_folder, "folder entries (no content_hash) should not affect the signature"


def test_040_load_credentials_from_env_vars(monkeypatch):
    monkeypatch.setenv("DROPBOX_APP_KEY", "test_key")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "test_token")
    assert load_credentials() == ("test_key", "test_token")


def test_050_load_credentials_from_file(monkeypatch, tmp_path):
    monkeypatch.delenv("DROPBOX_APP_KEY", raising=False)
    monkeypatch.delenv("DROPBOX_REFRESH_TOKEN", raising=False)
    cred_file = tmp_path / "dropbox_credentials.json"
    cred_file.write_text(json.dumps({"app_key": "file_key", "refresh_token": "file_token"}))

    import molass.DataUtils.DropboxSync as dropbox_sync
    monkeypatch.setattr(dropbox_sync, "_CRED_FILE", cred_file)
    assert load_credentials() == ("file_key", "file_token")


def test_060_load_credentials_missing_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("DROPBOX_APP_KEY", raising=False)
    monkeypatch.delenv("DROPBOX_REFRESH_TOKEN", raising=False)

    import molass.DataUtils.DropboxSync as dropbox_sync
    monkeypatch.setattr(dropbox_sync, "_CRED_FILE", tmp_path / "does_not_exist.json")
    try:
        load_credentials()
        assert False, "should have raised EnvironmentError"
    except EnvironmentError:
        pass
