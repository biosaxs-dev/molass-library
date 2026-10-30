"""molass.analysis_status (light status, #352) and AnalysisStatus.diagnose() (#353), on synthetic analysis folders."""
import json
import os

import numpy as np
import pytest

import molass
from molass.Rigorous.AnalysisFolder import AnalysisInfo
from molass.Rigorous.AnalysisStatus import AnalysisStatus, analysis_status


def _write_job(folder, job_id, entries, bounds=None):
    """entries: list of (fv, params); entry 0 is the starting point, as in a real callback.txt."""
    job = os.path.join(folder, "optimized", "jobs", job_id)
    os.makedirs(job, exist_ok=True)
    lines = []
    for c, (fv, params) in enumerate(entries):
        lines += ["t=2026-10-30 09:52:10", "x=", "[" + " ".join(f"{v:.17e}" for v in params) + "]",
                  f"f={fv}", f"a={c == 0 and 'False' or 'True'}", f"c={c}"]
    with open(os.path.join(job, "callback.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    if bounds is not None:
        np.savetxt(os.path.join(job, "bounds.txt"), np.asarray(bounds))


def _make(tmp_path, jobs, recipe=None, bounds=None, name="analysis-x"):
    folder = str(tmp_path / name)
    os.makedirs(os.path.join(folder, "optimized"))
    with open(os.path.join(folder, "optimized", "recipe.json"), "w") as f:
        json.dump(recipe if recipe is not None else dict(model="grm", num_components=1, fronting=[False]), f)
    for job_id, entries in jobs.items():
        _write_job(folder, job_id, entries, bounds)
    return folder


P = [0.5, 1.5, 2.5]


def _improving():
    return {"000": [(-1.0, P), (-1.2, [0.6, 1.5, 2.5]), (-1.1, P)],
            "001": [(-1.2, P), (-1.4, [0.7, 1.5, 2.5]), (-1.3, P)],
            "002": [(-1.4, P), (-1.6, [0.8, 1.6, 2.5])]}


def test_status_reads_the_files_only(tmp_path):
    st = analysis_status(_make(tmp_path, _improving()))
    assert isinstance(st, AnalysisStatus)
    assert st.n_jobs == 3 and st.n_iterations == 8
    assert st.fv == pytest.approx(-1.6) and st.best_job.id == "002"
    assert st.start_fv == pytest.approx(-1.0)
    assert st.sv == pytest.approx(-200 / (1 + np.exp(-1.5 * -1.6)) + 100)
    assert np.allclose(st.best_params, [0.8, 1.6, 2.5])             # the parameter vector of the best entry
    assert st.n_nonfinite == 0 and st.stalled_jobs == 0
    assert st.diagnose() == []
    text = st.summary()
    assert "best: job 002, fv=-1.6000" in text and "warning" not in text
    assert "AnalysisStatus('analysis-x'" in repr(st)


def test_light_load_analysis_is_the_same_status(tmp_path):
    folder = _make(tmp_path, _improving())
    st = molass.load_analysis(folder, light=True)
    assert isinstance(st, AnalysisStatus) and st.fv == pytest.approx(-1.6)
    assert molass.analysis_status(folder).fv == st.fv


def test_status_of_a_missing_folder_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        analysis_status(str(tmp_path / "nope"))


def test_status_without_jobs_or_recipe(tmp_path):
    folder = str(tmp_path / "empty")
    os.makedirs(folder)
    st = analysis_status(folder)
    assert st.jobs == [] and st.fv is None and st.sv is None and st.best_params is None
    assert st.diagnose() == [] and "none yet" in st.summary()


def test_is_active_follows_the_manifest():
    assert AnalysisStatus("f", {}, [], {"status": "running"}).is_active
    assert not AnalysisStatus("f", {}, [], {"status": "completed"}).is_active
    assert not AnalysisStatus("f", {}, [], None).is_active


def test_no_job_improved_on_the_starting_point(tmp_path):
    jobs = {j: [(-1.6518, P), (-1.50, P), (-1.60, P)] for j in ("000", "001", "002", "003")}
    st = analysis_status(_make(tmp_path, jobs, dict(model="grm")))
    findings = st.diagnose()
    assert any("no job improved on the starting point" in f and "-1.6518" in f for f in findings)
    assert any("did not improve the best objective value" in f for f in findings)
    assert "warning: no job improved" in st.summary()


def test_stalled_jobs_threshold(tmp_path):
    jobs = _improving()
    for j in ("003", "004", "005"):
        jobs[j] = [(-1.6, P), (-1.5, P)]
    st = analysis_status(_make(tmp_path, jobs))
    assert st.stalled_jobs == 3
    assert any("last 3 of 6 jobs" in f for f in st.diagnose())
    assert not any("last" in f for f in st.diagnose(stalled_after=4))


def test_nonfinite_fraction(tmp_path):
    jobs = {"000": [(-1.0, P)] + [(float("inf"), P)] * 2 + [(-1.2, P)] * 5,
            "001": [(-1.2, P), (-1.3, P)] + [(float("inf"), P)] * 2}
    st = analysis_status(_make(tmp_path, jobs))
    assert st.n_nonfinite == 4
    assert any("4 of 12 iterations were rejected as non-finite (33 %)" in f for f in st.diagnose())
    assert not any("non-finite" in f for f in st.diagnose(nonfinite_fraction=0.5))


@pytest.mark.parametrize("model, recipe_has_key, warned", [("egh", False, True), ("edm", False, True),
                                                           ("egh", True, False), ("grm", False, False)])
def test_recipe_without_the_fronting_key(tmp_path, model, recipe_has_key, warned):
    recipe = dict(model=model, num_components=1)
    if recipe_has_key:
        recipe["fronting"] = [True]
    st = analysis_status(_make(tmp_path, _improving(), recipe))
    assert any("no 'fronting' key" in f for f in st.diagnose()) is warned


def test_parameters_at_a_bound(tmp_path):
    bounds = [[0.0, 1.0], [1.0, 2.0], [2.5, 2.5]]                    # the last one is fixed (no width)
    jobs = {"000": [(-1.0, [0.5, 1.5, 2.5]), (-1.2, [1.0, 1.0, 2.5])]}
    st = analysis_status(_make(tmp_path, jobs, bounds=bounds))
    assert st.bounds.shape == (3, 2)
    findings = [f for f in st.diagnose() if "bound" in f]
    assert findings == ["2 of 3 parameters of the best entry are at a bound (parameter indices 0, 1)"]
    jobs = {"000": [(-1.0, [0.5, 1.5, 2.5]), (-1.2, [0.4, 1.4, 2.5])]}
    inside = analysis_status(_make(tmp_path, jobs, bounds=bounds, name="analysis-y"))
    assert not any("bound" in f for f in inside.diagnose())


def test_no_bounds_file_means_no_bound_check(tmp_path):
    st = analysis_status(_make(tmp_path, _improving()))
    assert st.bounds is None and not any("bound" in f for f in st.diagnose())


def test_analysis_info_is_a_status_with_diagnose_and_the_old_summary(tmp_path):
    class _Result:
        fv, sv = -1.5, 80.0

        def get_skewnesses(self):
            return [0.25]

    folder = _make(tmp_path, _improving())
    info = AnalysisInfo(folder, _Result(), "002", None, None, None,
                        dict(model="grm", fronting=[False]), analysis_status(folder).jobs, None)
    assert isinstance(info, AnalysisStatus)
    assert info.diagnose() == []
    text = info.summary()
    assert "result: job 002, fv=-1.5000, sv=80.00" in text and "component skewness" in text
    assert "best: job" not in text                                  # the light line is replaced, not repeated
