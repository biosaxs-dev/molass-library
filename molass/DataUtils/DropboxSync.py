"""
    DataUtils.DropboxSync.py

    Cache a Dropbox folder locally via the Dropbox API, for use as
    SecSaxsData input. Avoids the repeated re-downloads that can happen
    when reading directly from a Dropbox-desktop-synced ("Smart Sync"
    online-only) folder: each read may re-fetch content from the cloud
    instead of using a persistent local copy.

    A folder is downloaded in ONE request via files_download_zip_to_file
    (Dropbox zips it server-side), rather than one request per file --
    with many small SEC-SAXS frame files, per-file downloads are dominated
    by round-trip latency. A local sync-state file records a signature
    (from content_hash of every entry), so an unchanged folder costs only
    a metadata listing on repeat calls, no content transfer at all.

    The zip endpoint has limits (folder <20GB, <10,000 total entries, each
    file <4GB); if a folder exceeds them, sync_folder() automatically
    falls back to downloading file-by-file (skipping files whose local
    content_hash already matches).

    Requires the optional 'dropbox' extra: pip install molass[dropbox]

    One-time setup
    ---------------
    1. Create a scoped Dropbox app: https://www.dropbox.com/developers/apps
       - "Scoped access", access type "Full Dropbox" (or "App folder").
       - Under Permissions, enable `files.metadata.read` and
         `files.content.read`, then click Submit.
    2. Authorize once (PKCE flow -- no app secret needed):
           python -m molass.DataUtils.DropboxSync --authorize --app-key <your app key>
       This saves DROPBOX_APP_KEY / DROPBOX_REFRESH_TOKEN to
       ~/.molass/dropbox_credentials.json. Alternatively, set those two
       as environment variables instead of using the credentials file.

    Usage
    ------
        from molass.DataUtils import sync_dropbox_folder
        DATA_ROOT = sync_dropbox_folder("/MOLASS/Data/20260728/Y17AH20N")
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

_CRED_FILE = Path.home() / ".molass" / "dropbox_credentials.json"
_DEFAULT_CACHE_ROOT = Path.home() / ".molass" / "dropbox_cache"


def _require_dropbox():
    try:
        import dropbox
    except ImportError as e:
        raise ImportError(
            "Dropbox support requires the optional 'dropbox' package. "
            "Install with: pip install molass[dropbox]"
        ) from e
    return dropbox


def load_credentials() -> tuple[str, str]:
    """Return (app_key, refresh_token) from env vars or the credentials file."""
    app_key = os.environ.get("DROPBOX_APP_KEY")
    refresh_token = os.environ.get("DROPBOX_REFRESH_TOKEN")
    if app_key and refresh_token:
        return app_key, refresh_token
    if _CRED_FILE.exists():
        data = json.loads(_CRED_FILE.read_text())
        return data["app_key"], data["refresh_token"]
    raise EnvironmentError(
        "Dropbox credentials not found. Set DROPBOX_APP_KEY / DROPBOX_REFRESH_TOKEN "
        f"env vars, or run the one-time authorize() flow (see this module's docstring) "
        f"to create {_CRED_FILE}."
    )


def get_client(dbx=None):
    """Return dbx unchanged if given, otherwise build one from load_credentials()."""
    if dbx is not None:
        return dbx
    dropbox = _require_dropbox()
    app_key, refresh_token = load_credentials()
    return dropbox.Dropbox(oauth2_refresh_token=refresh_token, app_key=app_key)


def _local_content_hash(path: Path) -> str:
    from dropbox.content_hash import DropboxContentHasher

    hasher = DropboxContentHasher()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _state_file_for(local_root: Path) -> Path:
    # kept alongside (not inside) local_root: bulk zip sync replaces the
    # whole folder, which would otherwise delete an in-folder state file
    return local_root.parent / (local_root.name + ".dropbox_sync_state.json")


def _load_sync_state(local_root: Path) -> dict:
    state_file = _state_file_for(local_root)
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {}


def _save_sync_state(local_root: Path, state: dict) -> None:
    _state_file_for(local_root).write_text(json.dumps(state, indent=2))


def _list_all(dbx, dropbox_path: str) -> list:
    entries = []
    result = dbx.files_list_folder(dropbox_path, recursive=True)
    entries.extend(result.entries)
    while result.has_more:
        result = dbx.files_list_folder_continue(result.cursor)
        entries.extend(result.entries)
    return entries


def _folder_signature(entries: list, dropbox_path: str) -> str:
    import hashlib

    lines = sorted(
        f"{e.path_display[len(dropbox_path):].lstrip('/')}|{e.content_hash}|{e.size}"
        for e in entries
        if getattr(e, "content_hash", None) is not None
    )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _zip_sync(dbx, dropbox_path: str, local_root: Path) -> None:
    """Download the whole folder in one request and extract it in place."""
    import shutil
    import tempfile
    import zipfile

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "download.zip"
        dbx.files_download_zip_to_file(str(zip_path), dropbox_path)

        extract_dir = Path(tmpdir) / "extracted"
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        # Dropbox wraps the result in a single top-level folder entry.
        children = list(extract_dir.iterdir())
        src = children[0] if len(children) == 1 and children[0].is_dir() else extract_dir

        if local_root.exists():
            shutil.rmtree(local_root)
        local_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(local_root))


def _per_file_sync(dbx, dropbox_path: str, local_root: Path, entries: list) -> None:
    """Fallback for folders too big for the zip endpoint: download file by
    file, skipping any whose local content already matches."""
    local_root.mkdir(parents=True, exist_ok=True)
    n_downloaded = n_skipped = 0
    for entry in entries:
        if getattr(entry, "content_hash", None) is None:
            continue
        rel_path = entry.path_display[len(dropbox_path):].lstrip("/")
        local_path = local_root / rel_path.replace("/", os.sep)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        if local_path.exists() and _local_content_hash(local_path) == entry.content_hash:
            n_skipped += 1
            continue
        dbx.files_download_to_file(str(local_path), entry.path_lower)
        n_downloaded += 1
    print(f"  per-file fallback: {n_downloaded} downloaded, {n_skipped} up to date")


def sync_folder(dropbox_path: str, cache_root: Optional[str] = None, dbx=None, force: bool = False) -> str:
    """
    Mirror a Dropbox folder into a local cache. Returns the local path to
    use as SecSaxsData input. Downloads the whole folder in one request
    when anything has changed (or nothing at all when it hasn't); falls
    back to per-file downloads only if the folder is too large for that
    endpoint.

    Parameters
    ----------
    dropbox_path : str
        Dropbox-relative path, e.g. "/MOLASS/Data/20260728/Y17AH20N".
    cache_root : str, optional
        Local cache root. Defaults to ~/.molass/dropbox_cache/.
    dbx : dropbox.Dropbox, optional
        Reuse an existing client instead of building one from credentials.
    force : bool, optional
        Re-download even if the local cache signature already matches.
    """
    dropbox = _require_dropbox()
    dbx = get_client(dbx)
    cache_root_path = Path(cache_root) if cache_root else _DEFAULT_CACHE_ROOT
    local_root = cache_root_path / dropbox_path.strip("/").replace("/", os.sep)

    entries = _list_all(dbx, dropbox_path)
    signature = _folder_signature(entries, dropbox_path)
    state = _load_sync_state(local_root)

    if not force and local_root.exists() and state.get("signature") == signature:
        print(f"sync_folder({dropbox_path!r}): up to date -> {local_root}")
        return str(local_root)

    try:
        _zip_sync(dbx, dropbox_path, local_root)
        print(f"sync_folder({dropbox_path!r}): synced via bulk zip -> {local_root}")
    except dropbox.exceptions.ApiError as e:
        if isinstance(e.error, dropbox.files.DownloadZipError) and (
            e.error.is_too_large() or e.error.is_too_many_files()
        ):
            print(f"sync_folder({dropbox_path!r}): folder too large for bulk zip, falling back to per-file")
            _per_file_sync(dbx, dropbox_path, local_root, entries)
        else:
            raise

    state["signature"] = signature
    _save_sync_state(local_root, state)
    return str(local_root)


def start_authorize(app_key: str):
    """
    Begin the OAuth PKCE authorization flow (no app secret needed).

    Returns an auth_flow object. Call auth_flow.start() for the URL the
    user must visit and click "Allow" on, then pass the resulting code to
    finish_authorize(). Split into two steps (rather than a single
    blocking call) so a GUI can drive it with its own dialogs instead of
    a console input() prompt.
    """
    dropbox = _require_dropbox()
    return dropbox.DropboxOAuth2FlowNoRedirect(app_key, use_pkce=True, token_access_type="offline")


def finish_authorize(auth_flow, auth_code: str) -> tuple[str, str]:
    """Complete authorization. Returns (app_key, refresh_token)."""
    result = auth_flow.finish(auth_code.strip())
    return auth_flow.consumer_key, result.refresh_token


def save_credentials(app_key: str, refresh_token: str, path: Optional[Path] = None) -> Path:
    """Save credentials to the user-level credentials file (or a custom path)."""
    path = path or _CRED_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"app_key": app_key, "refresh_token": refresh_token}, indent=2))
    return path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dropbox cache setup/utilities")
    parser.add_argument("--authorize", action="store_true", help="Run one-time OAuth setup (console)")
    parser.add_argument("--app-key", help="Dropbox app key (for --authorize)")
    args = parser.parse_args()

    if args.authorize:
        key_in = args.app_key or input("App key: ").strip()
        flow = start_authorize(key_in)
        print("1. Go to:", flow.start())
        print('2. Click "Allow" (log in first if needed).')
        code = input("3. Enter the authorization code here: ")
        key_out, token = finish_authorize(flow, code)
        saved_path = save_credentials(key_out, token)
        print(f"\nSaved credentials to {saved_path}")
    else:
        parser.print_help()
