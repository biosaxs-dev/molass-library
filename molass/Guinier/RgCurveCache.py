"""Persistent, input-validated cache for per-frame Rg curves."""
import hashlib
import json
import logging
import os
import tempfile
from types import SimpleNamespace

import numpy as np

logger = logging.getLogger(__name__)


def _metadata(ssd):
    digest = hashlib.sha256()
    xr = ssd.xr
    for name in ("M", "qv", "jv", "E"):
        value = getattr(xr, name, None)
        digest.update(name.encode("ascii"))
        if value is None:
            digest.update(b"<none>")
            continue
        array = np.asarray(value)
        if array.dtype.hasobject:
            raise TypeError(f"cannot cache Rg curves for object-valued XR data: {name}")
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(repr(array.shape).encode("ascii"))
        digest.update(np.ascontiguousarray(array).tobytes())

    trimming = getattr(ssd, "trimming", None)
    xr_slices = getattr(trimming, "xr_slices", None)
    if xr_slices is not None:
        xr_slices = [
            None if item is None else [item.start, item.stop, item.step]
            for item in xr_slices
        ]
    import molass
    return {
        "format": 1,
        "molass_version": str(molass.__version__),
        "data_sha256": digest.hexdigest(),
        "small_angle_limit": getattr(trimming, "small_angle_limit", None),
        "xr_slices": xr_slices,
    }


def ssd_cache_path(cache_dir, ssd):
    """File in ``cache_dir`` for the Rg curve of ``ssd`` (molass-library#376): named by a hash of the XR
    data and the trimming (the molass version is checked inside the file, like for analysis folders)."""
    metadata = _metadata(ssd)
    key = {k: v for k, v in metadata.items() if k != "molass_version"}
    digest = hashlib.sha256(json.dumps(key, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    return os.path.join(cache_dir, f"rgcurve-{digest}.npz")


def load_rg_curve_cache(path, ssd):
    """Return a matching cached RgCurve, or None when no usable cache exists."""
    if not os.path.isfile(path):
        return None
    try:
        with np.load(path, allow_pickle=False) as archive:
            stored_metadata = json.loads(archive["metadata"].item())
            if stored_metadata != _metadata(ssd):
                return None
            frames = np.asarray(archive["frames"], dtype=int)
            rgs = np.asarray(archive["rgs"], dtype=float)
            scores = np.asarray(archive["scores"], dtype=float)
            i0s = np.asarray(archive["i0s"], dtype=float)
            i0_errors = np.asarray(archive["i0_errors"], dtype=float)
            score_source = str(archive["score_source"].item()) or None
    except (OSError, ValueError, KeyError) as error:
        logger.warning("Ignoring unreadable Rg-curve cache %s: %s", path, error)
        return None

    has_guinier_results = np.isfinite(i0s).any() or np.isfinite(i0_errors).any()
    results = None
    if has_guinier_results:
        results = [
            SimpleNamespace(
                I0=float(i0) if np.isfinite(i0) else None,
                I0_stdev=float(error) if np.isfinite(error) else None,
            )
            for i0, error in zip(i0s, i0_errors)
        ]
    from molass.Guinier.RgCurve import RgCurve
    return RgCurve(frames, rgs, scores, results=results, score_source=score_source)


def save_rg_curve_cache(path, ssd, curve):
    """Atomically save the derived Rg-curve values and their input fingerprint."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    i0s = np.asarray(curve.i0s, dtype=float)
    i0_errors = np.asarray(curve.i0_errors, dtype=float)
    metadata = json.dumps(_metadata(ssd), sort_keys=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w+b", dir=parent, suffix=".npz", delete=False) as output:
            temp_path = output.name
            np.savez_compressed(
                output,
                metadata=np.asarray(metadata),
                frames=np.asarray(curve.frames, dtype=int),
                rgs=np.asarray(curve.rgs, dtype=float),
                scores=np.asarray(curve.scores, dtype=float),
                i0s=i0s,
                i0_errors=i0_errors,
                score_source=np.asarray(getattr(curve, "score_source", None) or ""),
            )
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and os.path.exists(temp_path):
            os.unlink(temp_path)
