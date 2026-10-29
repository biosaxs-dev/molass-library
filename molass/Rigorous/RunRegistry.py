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


def read_manifest(folder, refresh=False):
    """Return the manifest dict in ``folder``, or ``None`` if absent / unreadable.

    The stored ``status`` / ``phase`` are written by whoever launched the run, and nothing
    updates them while a run in another process (e.g. the GUI's optimizer subprocess) progresses.
    With ``refresh=True`` they are first re-derived from the process table and the job files
    (see :func:`refresh_run_manifest`).
    """
    if refresh:
        refreshed = refresh_run_manifest(folder)
        if refreshed is not None:
            return refreshed
    path = os.path.join(folder, MANIFEST_NAME)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


# A run with no live subprocess is taken as finished when no job file was written for this long
# (the callback of one iteration can take many minutes on large data).
STALE_AFTER_S = 1800

# A recorded 'completed' / 'failed' is contradicted only by a callback.txt written more than this many seconds after it.
FINAL_STATUS_MARGIN_S = 10


def _pid_alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        pass
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _latest_job_activity(folder, names=("callback.txt", "optimizer.log")):
    """Latest modification time (epoch seconds) of the given files (default ``callback.txt`` / ``optimizer.log``) of the jobs."""
    jobs_folder = os.path.join(folder, "optimized", "jobs")
    latest = None
    try:
        for job in os.listdir(jobs_folder):
            for name in names:
                try:
                    mtime = os.path.getmtime(os.path.join(jobs_folder, job, name))
                except OSError:
                    continue
                if latest is None or mtime > latest:
                    latest = mtime
    except OSError:
        pass
    return latest


def _manifest_stamp(manifest):
    """Epoch seconds of the last write of the manifest (``last_updated``, else ``start_time``)."""
    for key in ("last_updated", "start_time"):
        try:
            return datetime.fromisoformat(manifest[key]).timestamp()
        except (KeyError, TypeError, ValueError):
            continue
    return 0.0


def refresh_run_manifest(folder, stale_after_s=STALE_AFTER_S):
    """Bring ``status`` / ``phase`` of the manifest in an analysis folder up to date, and return it.

    ``RUN_MANIFEST.json`` is written when a run starts; the optimizer subprocess does not touch it
    afterwards, so ``status`` stayed ``'running'`` for ever, or said ``'completed'`` while chained jobs
    were still being added to the folder (#345). This derives the state from what is on disk:

    1. the recorded ``subprocess_pid`` is alive, or a job file (``callback.txt``, ``optimizer.log``)
       was written within ``stale_after_s`` seconds: ``status='running'``, ``phase='optimizing'``
       (a recorded ``'completed'`` / ``'failed'`` is the launching process's word: only a ``callback.txt``
       written more than ``FINAL_STATUS_MARGIN_S`` seconds after it was recorded, i.e. a further job
       chained in the same folder, contradicts it; neither ``optimizer.log`` nor a live pid does, since
       logging can touch the log after the run ended and a pid can be reused);
    2. otherwise a manifest still saying ``'running'`` / ``'starting'`` becomes ``'completed'``,
       ``phase='finished'`` (the return code of a process that is gone is not known; a recorded
       ``'failed'`` is kept);
    3. with no process and no job file at all (a run that has just been launched) nothing changes.

    ``status`` describes the analysis folder as a whole, so it is ``'running'`` while any of its (chained)
    jobs is active; ``jobs/NNN/RUN_MANIFEST.json`` keeps the state of the single job.

    Also stores the progress numbers ``n_jobs``, ``n_callbacks``, ``n_nonfinite`` (entries rejected as
    non-finite, #346), ``stalled_jobs``, ``best_fv`` and ``last_callback_time`` (UTC ISO), and
    ``status_source`` (``'pid'``, ``'job_files'`` or ``'stored'``). The file is rewritten only when
    one of them changed. Errors are swallowed; returns ``None`` if the folder has no manifest.
    """
    path = os.path.join(folder, MANIFEST_NAME)
    if not os.path.exists(path) or not os.path.isdir(os.path.join(folder, "optimized", "jobs")):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    try:
        changes = {}
        status = manifest.get("status")
        sub_pid = manifest.get("subprocess_pid")
        last_activity = _latest_job_activity(folder)
        last_callback = _latest_job_activity(folder, names=("callback.txt",))
        if status in ("completed", "failed"):
            # A final status is the launching process's word. Only a callback.txt written clearly after it
            # (a further job chained in the same folder) contradicts it: optimizer.log can be touched by
            # logging after the run ended, and a recorded pid may have been reused by another process.
            chained = (last_callback is not None
                       and last_callback > _manifest_stamp(manifest) + FINAL_STATUS_MARGIN_S
                       and time.time() - last_callback < stale_after_s)
            new_status, source = ("running", "job_files") if chained else (status, "stored")
        else:
            recent = last_activity is not None and time.time() - last_activity < stale_after_s
            if sub_pid is not None and _pid_alive(sub_pid):
                new_status, source = "running", "pid"
            elif recent:
                new_status, source = "running", "job_files"
            elif status in ("running", "starting") and (sub_pid is not None or last_activity is not None):
                new_status, source = "completed", "job_files"
            else:
                new_status, source = status, "stored"
        if new_status != status:
            changes["status"] = new_status
            changes["phase"] = "optimizing" if new_status == "running" else "finished"
        elif status == "completed" and manifest.get("phase") in ("folders_prepared", "constructing_optimizer", "optimizer_ready"):
            changes["phase"] = "finished"
        if manifest.get("status_source") != source:
            changes["status_source"] = source
        if last_callback is not None:
            stamp = datetime.fromtimestamp(last_callback, timezone.utc).isoformat(timespec="seconds")
            if manifest.get("last_callback_time") != stamp:
                changes["last_callback_time"] = stamp

        try:
            from molass.Rigorous.CurrentStateUtils import list_rigorous_jobs, count_stalled_jobs
            jobs = list_rigorous_jobs(folder)
            stats = {
                "n_jobs": len(jobs),
                "n_callbacks": sum(j.n_entries for j in jobs),
                "n_nonfinite": sum(j.n_nonfinite for j in jobs),
                "stalled_jobs": count_stalled_jobs(jobs),
                "best_fv": min((j.best_fv for j in jobs), default=None),
            }
            for key, value in stats.items():
                if manifest.get(key) != value:
                    changes[key] = value
        except Exception:
            pass

        if changes:
            updated = update_run_manifest(folder, **changes)
            if updated is not None:
                return updated
            manifest.update(changes)
        return manifest
    except Exception:
        return manifest


def locate_recent_runs(since_minutes=60, registry_path=None, refresh=True):
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
    refresh : bool, optional
        Re-derive each manifest's ``status`` / ``phase`` from the disk first
        (:func:`refresh_run_manifest`).  Default True.

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
                rec["manifest"] = read_manifest(rec["folder"], refresh=refresh) if rec["exists"] else None
                entries.append(rec)
    except OSError:
        return []

    entries.sort(key=lambda r: r.get("start_time", ""), reverse=True)
    return entries
