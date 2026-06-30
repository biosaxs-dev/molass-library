"""
    Rigorous.RunRegistry
    ====================

    Disk-side breadcrumbs for rigorous optimization runs.

    Why this exists
    ---------------
    A rigorous optimization can run for hours.  Once launched (especially
    via ``compare_optimization_paths`` with ``monitor=False``), the parent
    Python kernel may be busy and unable to answer "what is running right
    now?" from outside.  External observers (a second VS Code session,
    an AI assistant, a shell) need an *out-of-band* way to find live runs
    without parsing process trees or guessing folder names.

    The registry solves this by writing two artifacts:

    1. A per-run ``RUN_MANIFEST.json`` inside each ``analysis_folder``
       (and, once known, inside the legacy ``work_folder`` too), recording
       method / niter / pid / start time / paths.

    2. An append-only ``~/.molass/runs.jsonl`` global registry — one line
       per run start.  Cheap to scan; never rewritten.

    Both files are best-effort: any I/O error is swallowed so the
    optimizer itself never fails because of bookkeeping.

    Public helpers
    --------------
    - :func:`write_run_manifest`  — drop a manifest at run start
    - :func:`update_run_manifest` — merge fields into an existing manifest
    - :func:`read_manifest`       — read a single manifest
    - :func:`locate_recent_runs`  — list recently-started runs
"""
import json
import os
import time
from datetime import datetime, timezone

SCHEMA = "molass.run_manifest/v1"
MANIFEST_NAME = "RUN_MANIFEST.json"


def _registry_path():
    return os.path.join(os.path.expanduser("~"), ".molass", "runs.jsonl")


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_run_manifest(folder, **fields):
    """Write ``RUN_MANIFEST.json`` into ``folder`` and append a registry line.

    All errors are swallowed.  Returns the manifest dict on success,
    ``None`` on failure.

    Parameters
    ----------
    folder : str
        Absolute path of the folder to drop the manifest into.  Must
        already exist.
    **fields
        Arbitrary JSON-serializable keys merged into the manifest.
        Common keys: ``method``, ``niter``, ``in_process``, ``monitor``,
        ``analysis_folder``, ``role`` ('analysis' or 'work').
    """
    try:
        manifest = {
            "schema": SCHEMA,
            "pid": os.getpid(),
            "start_time": _now_iso(),
            "folder": os.path.abspath(folder),
        }
        manifest.update(fields)
        path = os.path.join(folder, MANIFEST_NAME)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str)

        # Append to global registry (best effort).
        try:
            reg = _registry_path()
            os.makedirs(os.path.dirname(reg), exist_ok=True)
            with open(reg, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "folder": manifest["folder"],
                    "start_time": manifest["start_time"],
                    "pid": manifest["pid"],
                    "method": fields.get("method"),
                    "niter": fields.get("niter"),
                    "role": fields.get("role"),
                }) + "\n")
        except OSError:
            pass

        return manifest
    except OSError:
        return None


def update_run_manifest(folder, **fields):
    """Merge ``fields`` into an existing manifest in ``folder``.

    Creates the file if missing.  Errors swallowed.
    """
    try:
        path = os.path.join(folder, MANIFEST_NAME)
        existing = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (OSError, json.JSONDecodeError):
                existing = {}
        existing.update(fields)
        existing["last_updated"] = _now_iso()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, default=str)
        return existing
    except OSError:
        return None


def read_manifest(folder):
    """Return the manifest dict in ``folder``, or ``None`` if absent / unreadable."""
    path = os.path.join(folder, MANIFEST_NAME)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def locate_recent_runs(since_minutes=60, registry_path=None):
    """Return a list of recently-started runs (newest first).

    Reads the global registry at ``~/.molass/runs.jsonl`` and filters by
    start time.  Each entry is augmented with ``exists`` (folder still on
    disk) and ``manifest`` (the live manifest dict, if readable — may
    contain status fields like ``subprocess_returncode`` written later).

    Parameters
    ----------
    since_minutes : float, optional
        Window for "recent".  Default 60.
    registry_path : str, optional
        Override registry location (mainly for tests).

    Returns
    -------
    list of dict
        Each dict has at least ``folder``, ``start_time``, ``pid``,
        ``method``, ``niter``, ``role``, ``exists``, ``manifest``.
    """
    reg = registry_path or _registry_path()
    if not os.path.exists(reg):
        return []

    cutoff = time.time() - since_minutes * 60
    entries = []
    try:
        with open(reg, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = rec.get("start_time")
                if ts:
                    try:
                        when = datetime.fromisoformat(ts).timestamp()
                    except ValueError:
                        when = 0
                    if when < cutoff:
                        continue
                rec["exists"] = os.path.isdir(rec.get("folder", ""))
                rec["manifest"] = read_manifest(rec["folder"]) if rec["exists"] else None
                entries.append(rec)
    except OSError:
        return []

    entries.sort(key=lambda r: r.get("start_time", ""), reverse=True)
    return entries
