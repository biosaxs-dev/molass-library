"""
    Rigorous.AnalysisFolder
    =======================

    One call to open an analysis folder (molass-library#344): ``molass.load_analysis(folder)``.
"""
import os
import json
import tempfile

import numpy as np
from molass.Rigorous.AnalysisStatus import AnalysisStatus


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _sample_xy(x, y, max_points=512):
    x = np.asarray(x)
    y = np.asarray(y)
    if len(x) > max_points:
        indices = np.linspace(0, len(x) - 1, max_points, dtype=int)
        x, y = x[indices], y[indices]
    return {"x": x, "y": y}


def _area(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    return float(np.sum((y[1:] + y[:-1]) * np.diff(x) / 2.0)) if len(x) > 1 else 0.0


def _curve_summary(curve):
    x, y = curve.get_xy()
    moment = curve.get_moment()
    mean, std = moment.get_meanstd()
    y_array = np.asarray(y, dtype=float)
    finite = np.isfinite(y_array)
    peak_index = int(np.nanargmax(y_array)) if finite.any() else None
    return {
        **_sample_xy(x, y),
        "moments": {"mean": mean, "std": std},
        "area": _area(x, y_array),
        "peak_index": peak_index,
        "peak_frame": None if peak_index is None else float(np.asarray(x)[peak_index]),
        "skewness": curve.skewness() if callable(getattr(curve, "skewness", None)) else None,
    }


class AnalysisInfo(AnalysisStatus):
    """Everything about a finished (or running) analysis folder, from :func:`load_analysis`.

    Extends :class:`~molass.Rigorous.AnalysisStatus.AnalysisStatus` (the files only: jobs, manifest, recipe,
    ``diagnose()``) with the rebuilt decomposition and the loaded result.

    Attributes
    ----------
    analysis_folder : str
    result : Decomposition or None
        The rigorous-optimization result of the selected job (``result.fv``, ``result.sv``),
        ``None`` while no job has produced a result yet.
    jobid : str or None
        The job ``result`` was loaded from.
    decomp : Decomposition
        The initial (estimator) decomposition rebuilt from the recipe.
    ssd, trimmed : SecSaxsData
        The raw and the trimmed data.
    recipe : dict
        The ``recipe.json`` contents.
    jobs : list of JobInfo
        Per job: ``best_fv``, ``iterations``, ``n_nonfinite`` (rejected iterations), ...
    manifest : dict or None
        ``RUN_MANIFEST.json`` with ``status`` / ``phase`` brought up to date.
    """

    def __init__(self, analysis_folder, result, jobid, decomp, ssd, trimmed, recipe, jobs, manifest):
        super().__init__(analysis_folder, recipe, jobs, manifest)
        self.result = result
        self.jobid = jobid
        self.decomp = decomp
        self.ssd = ssd
        self.trimmed = trimmed

    @property
    def fv(self):
        """Objective value of the loaded result (``None`` without a result)."""
        return None if self.result is None else getattr(self.result, 'fv', None)

    @property
    def sv(self):
        """Score value (0-100) of the loaded result (``None`` without a result)."""
        return None if self.result is None else getattr(self.result, 'sv', None)

    @property
    def component_skewness(self):
        """Skewness of the elution curve of each component of the result (negative = fronting);
        ``None`` without a result, or when the result cannot tell."""
        get = getattr(self.result, 'get_skewnesses', None)
        if get is None:
            return None
        return get()

    def describe(self):
        """List the main post-analysis accessors available from this loaded result."""
        if self.result is None:
            return "No completed result is available yet."
        return "\n".join((
            "Elution moments: result.xr_icurve.get_moment().get_meanstd()",
            "Component curves: result.xr_ccurves[k].get_moment().get_meanstd()",
            "Data Rg curve: decomp.get_rg_curve()",
            "Model Rg curve: result.compute_reconstructed_rgcurve()",
            "Scattering matrices (M, C, P, Pe): result.get_xr_matrices()",
            "Component Guinier fit: result.get_xr_components()[k].get_guinier_object()",
            "Kratky shape match: result.get_kratky_shape_match()",
            "LRF residual: result.get_lrf_residual()",
            "Freeze JSON: info.freeze(path, include=('curves', 'kratky', 'rgcurve'))",
        ))

    def _result_lines(self):
        if self.result is None:
            return ["result: none yet (no job has a real result)"]
        lines = [f"result: job {self.jobid}, fv={self.fv:.4f}, sv={self.sv:.2f}"]
        skews = self.component_skewness
        if skews is not None:
            lines.append("component skewness (negative = fronting): " + ", ".join(f"{s:.2f}" for s in skews))
        return lines

    def to_summary_dict(self, include=()):
        """Return a JSON-ready result summary, optionally including derived curves.

        ``include`` accepts ``'curves'`` (sampled XR/UV elution curves and moments),
        ``'kratky'`` (sampled component profiles and the shape-match result), and
        ``'rgcurve'`` (data and model-reconstructed per-frame Rg curves). These
        optional groups may trigger additional computations.
        """
        if isinstance(include, str):
            include = (include,)
        include = set(include)
        supported = {"curves", "kratky", "rgcurve"}
        unknown = include - supported
        if unknown:
            raise ValueError(f"unknown summary sections: {sorted(unknown)}")

        summary = {
            "analysis_folder": self.analysis_folder,
            "analysis_folder_name": os.path.basename(os.path.normpath(self.analysis_folder)),
            "jobid": self.jobid,
            "note": self.note,
            "moved_from": self.moved_from,
            "recipe": self.recipe,
            "changed_defaults": self.changed_defaults(),
            "manifest": self.manifest,
            "jobs": [
                {
                    "id": job.id,
                    "best_fv": job.best_fv,
                    "iterations": job.iterations,
                    "entries": job.n_entries,
                    "nonfinite": job.n_nonfinite,
                }
                for job in self.jobs
            ],
            "result": None,
        }
        if self.result is None:
            return _json_safe(summary)

        curves = list(self.result.xr_ccurves)
        guinier = self.result.get_guinier_objects()
        areas = [
            _area(*curve.get_xy())
            for curve in curves
        ]
        total_area = sum(areas)
        skewnesses = self.result.get_skewnesses()
        components = []
        for index, (curve, sg, area) in enumerate(zip(curves, guinier, areas)):
            x, y = curve.get_xy()
            y_array = np.asarray(y, dtype=float)
            peak_index = int(np.nanargmax(y_array)) if np.isfinite(y_array).any() else None
            params = curve.get_params() if callable(getattr(curve, "get_params", None)) else getattr(curve, "params", None)
            components.append({
                "index": index,
                "parameters": params,
                "area": area,
                "area_fraction": area / total_area if np.isfinite(total_area) and total_area != 0 else None,
                "peak_index": peak_index,
                "peak_frame": None if peak_index is None else float(np.asarray(x)[peak_index]),
                "rg": getattr(sg, "Rg", None),
                "i0": getattr(sg, "Iz", None),
                "guinier_score": getattr(sg, "score", None),
                "skewness": skewnesses[index],
            })

        summary["result"] = {
            "model": getattr(self.result, "model", None),
            "fv": self.fv,
            "sv": self.sv,
            "num_components": len(components),
            "components": components,
        }

        if "curves" in include:
            summary["curves"] = {
                "xr": {
                    "total": _curve_summary(self.result.xr_icurve),
                    "components": [_curve_summary(curve) for curve in curves],
                },
                "uv": None if self.result.uv_icurve is None else {
                    "total": _curve_summary(self.result.uv_icurve),
                    "components": [_curve_summary(curve) for curve in self.result.uv_ccurves],
                },
            }

        if "kratky" in include:
            _, _, profiles, _ = self.result.get_xr_matrices()
            q = self.result.xr.qv
            component_rgs = [getattr(sg, "Rg", None) for sg in guinier]
            component_i0s = [getattr(sg, "Iz", None) for sg in guinier]
            q = np.asarray(q)
            profiles = np.asarray(profiles)
            if len(q) > 512:
                indices = np.linspace(0, len(q) - 1, 512, dtype=int)
                q, profiles = q[indices], profiles[indices, :]
            summary["kratky"] = {
                "q": q,
                "profiles": profiles,
                "rgs": component_rgs,
                "i0s": component_i0s,
                "shape_match": self.result.get_kratky_shape_match().to_dict(),
            }

        if "rgcurve" in include:
            data_curve = self.result.get_rg_curve()
            model_curve = self.result.compute_reconstructed_rgcurve()
            summary["rgcurve"] = {
                "data": {
                    "frames": data_curve.frames,
                    "rgs": data_curve.rgs,
                    "scores": data_curve.scores,
                },
                "model": {
                    "frames": model_curve.frames,
                    "rgs": model_curve.rgs,
                },
            }
        return _json_safe(summary)

    def freeze(self, path, include=()):
        """Write :meth:`to_summary_dict` as strict JSON and return the file path."""
        path = os.path.abspath(os.fspath(path))
        parent = os.path.dirname(path)
        os.makedirs(parent, exist_ok=True)
        summary = self.to_summary_dict(include=include)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=parent, suffix=".tmp", delete=False
            ) as output:
                temp_path = output.name
                json.dump(summary, output, ensure_ascii=False, indent=2, allow_nan=False)
                output.write("\n")
            os.replace(temp_path, path)
        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)
        return path

    def __repr__(self):
        return f"AnalysisInfo({os.path.basename(os.path.normpath(self.analysis_folder))!r}, jobid={self.jobid!r}, fv={self.fv}, n_jobs={self.n_jobs})"


def load_analysis(analysis_folder, jobid='best', rgcurve=None, in_folder=None, light=False):
    """Open an analysis folder: best result, its score value, jobs, rejected iterations and recipe.

    The one call for "what happened in this analysis folder", whether the run is finished or still
    going. It rebuilds the decomposition from ``recipe.json``, loads the result of the job selected
    by ``jobid`` and lists the jobs; ``print(info)`` (or ``info.summary()``) answers the usual
    questions at once.

    Parameters
    ----------
    analysis_folder : str
        Same value passed to ``optimize_rigorously(analysis_folder=...)``.
    jobid : str or None, optional
        ``'best'`` (default) loads the job with the lowest objective value, ``None`` the latest
        valid job, anything else that job id (e.g. ``'001'``).
    rgcurve : RgCurve, optional
        Passed to ``load_rigorous_result`` to avoid recomputing the Rg curve.
    in_folder : str, optional
        Folder holding the input data, for an analysis folder made on another machine (#348).
    light : bool, optional
        ``True`` does not rebuild the decomposition: it returns the :class:`AnalysisStatus` of
        :func:`molass.analysis_status` (files only, seconds instead of minutes; no ``result``,
        ``decomp``, ``ssd``, ``trimmed``), and ``jobid``, ``rgcurve`` and ``in_folder`` are not used (#352).
        Default ``False``.

    Returns
    -------
    AnalysisInfo
        With ``result``, ``decomp``, ``ssd``, ``trimmed``, ``recipe``, ``jobs`` and ``manifest``.
        ``result`` is ``None`` while no job has a result yet. (:class:`AnalysisStatus` for ``light=True``.)

    Examples
    --------
    ::

        import molass
        info = molass.load_analysis("analysis-001")
        print(info)                       # result, SV, jobs, rejected iterations, recipe
        info.result.plot_components()
        info.sv, info.n_nonfinite
    """
    if light:
        from molass.Rigorous.AnalysisStatus import analysis_status
        return analysis_status(analysis_folder)
    from molass.Rigorous.RecipeRunner import rebuild_decomposition_from_recipe
    from molass.Rigorous.CurrentStateUtils import (
        list_rigorous_jobs, load_rigorous_result, fv_to_sv, NoCompletedJobError,
    )
    from molass.Rigorous.RunRegistry import read_manifest

    analysis_folder = os.path.abspath(analysis_folder)
    ssd, trimmed, decomp, recipe = rebuild_decomposition_from_recipe(analysis_folder, in_folder=in_folder)
    rg_cache_path = os.path.join(analysis_folder, "optimized", "cache", "rgcurve.npz")
    decomp._rg_curve_cache_path = rg_cache_path
    jobs = list_rigorous_jobs(analysis_folder)
    try:
        result = load_rigorous_result(decomp, analysis_folder, jobid=jobid, rgcurve=rgcurve)
    except NoCompletedJobError:
        result = None
    loaded = None
    if result is not None:
        result._rg_curve_cache_path = rg_cache_path
        if isinstance(jobid, str) and jobid != 'best':
            loaded = jobid
        elif jobs:
            loaded = (min(jobs, key=lambda j: j.best_fv) if jobid == 'best' else jobs[-1]).id
        job = next((j for j in jobs if j.id == loaded), None)
        if job is not None and getattr(result, 'fv', None) is None:
            result.fv = job.best_fv
            result.sv = float(fv_to_sv(job.best_fv))
    return AnalysisInfo(analysis_folder, result, loaded, decomp, ssd, trimmed, recipe, jobs,
                        read_manifest(analysis_folder, refresh=True))
