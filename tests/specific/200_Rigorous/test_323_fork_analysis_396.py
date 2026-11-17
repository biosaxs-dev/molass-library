"""Continue an analysis under another model or from a seed (molass-library#396): JobInfo.first_fv, the record of
the seed in recipe.json, the early check of the seed, and molass.fork_analysis."""
import json
import os
import shutil
import tempfile
import warnings

import numpy as np
import pytest

import molass
from molass.Rigorous.CurrentStateUtils import list_rigorous_jobs
from molass.Rigorous.ForkAnalysis import _resolve_seed, plan_fork
from molass.Rigorous.RigorousImplement import with_provenance
from molass.Rigorous.RunRegistry import refresh_run_manifest, write_run_manifest


def _write_job(folder, jobid, fvs):
    job_dir = os.path.join(folder, "optimized", "jobs", jobid)
    os.makedirs(job_dir, exist_ok=True)
    with open(os.path.join(job_dir, "callback.txt"), "w") as f:
        for i, fv in enumerate(fvs):
            f.write(f"t=2026-01-01 12:00:{i:02d}\n")
            f.write("x=\n[ 1.0]\n")
            f.write(f"f={fv}\n")
            f.write(f"a={'True' if i else 'False'}\n")
            f.write(f"c={i * 1000}\n")


def _write_recipe(folder, **fields):
    os.makedirs(os.path.join(folder, "optimized"), exist_ok=True)
    recipe = dict(model="egh", method="bh", num_components=3)
    recipe.update(fields)
    with open(os.path.join(folder, "optimized", "recipe.json"), "w") as f:
        json.dump(recipe, f)


# -- JobInfo.first_fv, start_fv, summary ------------------------------------------------------------------------

def test_job_info_has_the_fv_of_the_start(tmp_path):
    folder = str(tmp_path)
    _write_job(folder, "000", [-0.9715, -1.0, -1.08])
    _write_job(folder, "001", [-1.08, -1.2])
    first, second = list_rigorous_jobs(folder)
    assert first.first_fv == pytest.approx(-0.9715) and first.best_fv == pytest.approx(-1.08)
    assert second.first_fv == pytest.approx(-1.08)


def test_job_info_keeps_its_older_constructions():
    from molass.Rigorous.CurrentStateUtils import JobInfo
    assert JobInfo("000", 5, -1.0, None).first_fv is None
    assert JobInfo("000", 5, -1.0, None, 5, 0).first_fv is None


def test_status_manifest_and_summary_tell_what_the_run_started_from(tmp_path):
    folder = str(tmp_path)
    _write_recipe(folder, seeded_from="best of analysis-EGH (job 008)", forked_from="C:/x/analysis-EGH")
    write_run_manifest(folder, status="running", subprocess_pid=os.getpid())
    _write_job(folder, "000", [-0.9715, -1.0, -1.08])
    status = molass.analysis_status(folder)
    assert status.start_fv == pytest.approx(-0.9715)
    text = status.summary()
    assert "seeded from: best of analysis-EGH (job 008)" in text and "start fv=-0.9715" in text
    assert "forked from: C:/x/analysis-EGH" in text
    assert refresh_run_manifest(folder)["start_fv"] == pytest.approx(-0.9715)


# -- recipe provenance ------------------------------------------------------------------------------------------

def test_a_continued_folder_keeps_what_job_000_started_from(tmp_path):
    folder = str(tmp_path)
    _write_recipe(folder, seeded_from="best of A", seed_params=[1.0, 2.0], forked_from="C:/A")
    kept = with_provenance({"model": "egh"}, folder)
    assert kept["seeded_from"] == "best of A" and kept["seed_params"] == [1.0, 2.0] and kept["forked_from"] == "C:/A"
    replaced = with_provenance({"model": "egh", "seeded_from": "given vector", "seed_params": [3.0]}, folder)
    assert replaced["seeded_from"] == "given vector" and replaced["seed_params"] == [3.0]


# -- the seed is checked before anything is made ----------------------------------------------------------------

@pytest.fixture(scope="module")
def tiny():
    from molass.Testing import simulate_tiny
    trimmed = simulate_tiny().trimmed_copy()
    return trimmed, trimmed.corrected_copy().quick_decomposition(num_components=2)


@pytest.mark.parametrize("bad", [np.zeros(3), np.full(0, np.nan)])
def test_a_seed_of_the_wrong_length_raises_and_nothing_is_made(tiny, tmp_path, bad):
    trimmed, decomp = tiny
    folder = str(tmp_path / "run")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(ValueError, match="seed_params has"):
            decomp.optimize_rigorously(analysis_folder=folder, trimmed_ssd=trimmed, seed_params=bad,
                                       async_=False, monitor=False)
    assert not os.path.exists(folder)


def test_a_seed_with_nan_raises(tiny, tmp_path):
    trimmed, decomp = tiny
    seed = decomp.get_rigorous_initparams().copy()
    seed[0] = np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(ValueError, match="NaN or infinite"):
            decomp.optimize_rigorously(analysis_folder=str(tmp_path / "run"), trimmed_ssd=trimmed, seed_params=seed,
                                       async_=False, monitor=False)


def test_a_seed_starts_job_000_only_later_rounds_continue_from_the_best(tiny, tmp_path, monkeypatch):
    """With num_jobs > 1 every round used to get the seed, which takes priority over the resume from the best
    parameters: each round restarted from the seed."""
    import molass.LowRank.Decomposition as decomposition_module
    import molass.Rigorous.RigorousImplement as implement
    trimmed, decomp = tiny
    calls = []

    class Run:
        def wait(self, timeout=None):
            pass

    def fake(decomposition, rgcurve, **kwargs):
        calls.append((kwargs["clear_jobs"], kwargs["seed_params"]))
        return Run()

    monkeypatch.setattr(implement, "make_rigorous_decomposition_impl", fake)
    # optimize_rigorously reloads the module on every call, which would undo the patch
    monkeypatch.setattr(decomposition_module, "reload", lambda module: module)
    seed = decomp.get_rigorous_initparams()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        decomp.optimize_rigorously(analysis_folder=str(tmp_path / "run"), trimmed_ssd=trimmed, seed_params=seed,
                                   num_jobs=3, async_=False, monitor=False)
    assert [clear for clear, _ in calls] == [True, False, False]
    assert calls[0][1] is seed and calls[1][1] is None and calls[2][1] is None


# -- the arguments of fork_analysis ------------------------------------------------------------------------------

def test_the_seed_argument_is_resolved():
    assert _resolve_seed('auto', False, 'egh', 'egh') == ('best', None)
    assert _resolve_seed('auto', True, 'egh', 'grm') == ('converted', None)
    assert _resolve_seed(None, True, 'egh', 'grm') == ('none', None)
    kind, array = _resolve_seed([1, 2, 3], False, 'egh', 'egh')
    assert kind == 'given' and array.tolist() == [1.0, 2.0, 3.0]
    with pytest.raises(ValueError, match="parameter vectors differ"):
        _resolve_seed('best', True, 'egh', 'grm')
    with pytest.raises(ValueError, match="model change"):
        _resolve_seed('converted', False, 'egh', 'egh')
    with pytest.raises(ValueError, match="seed must be"):
        _resolve_seed('nonsense', False, 'egh', 'egh')


def test_fork_refuses_what_is_not_an_analysis_or_would_overwrite_one(tmp_path):
    with pytest.raises(FileNotFoundError, match="not an analysis folder"):
        molass.fork_analysis(str(tmp_path / "nothing"), str(tmp_path / "new"))
    source, new = str(tmp_path / "src"), str(tmp_path / "new")
    _write_recipe(source)
    os.makedirs(os.path.join(new, "optimized"))
    with pytest.raises(FileExistsError):
        molass.fork_analysis(source, new)


def test_bad_arguments_fail_before_the_source_is_loaded(tmp_path):
    egh, grm = str(tmp_path / "src_egh"), str(tmp_path / "src_grm")
    _write_recipe(egh)                  # no jobs: loading it would fail differently (and take minutes)
    _write_recipe(grm, model="grm")
    new = str(tmp_path / "new")
    with pytest.raises(ValueError, match="parameter vectors differ"):
        plan_fork(egh, new, model="grm", seed="best")
    with pytest.raises(ValueError, match="model must be"):
        plan_fork(egh, new, model="gauss")
    with pytest.raises(ValueError, match="not to EGH"):
        plan_fork(grm, new, model="egh")
    with pytest.raises(ValueError, match="needs model"):
        plan_fork(egh, new, match_curves=True)


# -- with a real finished analysis (slow) ------------------------------------------------------------------------

@pytest.fixture(scope="module")
def finished():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    trimmed = SSD(SAMPLE1).trimmed_copy()
    decomp = trimmed.corrected_copy().quick_decomposition(num_components=3)
    folder = tempfile.mkdtemp(prefix="test_fork_396_")
    source = os.path.join(folder, "analysis-A")
    decomp.optimize_rigorously(method='DE', niter=1, async_=False, monitor=False, trimmed_ssd=trimmed,
                               analysis_folder=source, note="the source")
    yield source, folder
    shutil.rmtree(folder, ignore_errors=True)


@pytest.mark.slow
def test_plan_of_a_fork_under_the_same_model_seeds_from_the_stored_best(finished):
    source, folder = finished
    plan = molass.fork_analysis(source, os.path.join(folder, "analysis-B"), dry_run=True)
    info = molass.load_analysis(source)
    assert plan.seed == 'best' and plan.model == plan.source_model == 'egh'
    np.testing.assert_allclose(plan.seed_params, info.result._rigorous_params)
    recipe = plan.recipe
    assert recipe['forked_from'] == os.path.abspath(source) and recipe['model'] == 'egh'
    assert 'analysis_folder_name' not in recipe and 'note' not in recipe     # the fork names itself
    assert plan.kwargs['seed_source'].startswith("best of analysis-A") and plan.kwargs['note'] == "forked from analysis-A"
    assert not os.path.exists(os.path.join(folder, "analysis-B"))            # a dry run makes nothing


@pytest.mark.slow
def test_plan_of_a_model_change_converts_the_best_result(finished):
    source, folder = finished
    plan = molass.fork_analysis(source, os.path.join(folder, "analysis-C"), model="lkm", match_curves=True,
                                dry_run=True)
    assert plan.seed == 'converted' and plan.model == 'lkm' and plan.source_model == 'egh'
    assert len(plan.seed_params) == plan.decomposition.get_rigorous_param_count()
    assert plan.recipe['model'] == 'lkm'
    assert 'function_code' not in plan.recipe and 'fronting' not in plan.recipe     # tied to the EGH layout
    assert plan.kwargs['function_code'] is None
    assert "converted to LKM, curves matched" in plan.seeded_from
    assert plan.decomposition.match_curves_info['improved']


@pytest.mark.slow
def test_a_given_seed_of_the_wrong_length_stops_the_launch(finished):
    source, folder = finished
    new = os.path.join(folder, "analysis-D")
    with pytest.raises(ValueError, match="seed_params has"):
        molass.fork_analysis(source, new, seed=[1.0, 2.0], async_=False, monitor=False)
    assert not os.path.exists(new)


@pytest.mark.slow
def test_a_fork_starts_from_the_best_of_its_source_and_says_so(finished):
    source, folder = finished
    new = os.path.join(folder, "analysis-E")
    src = molass.load_analysis(source)
    molass.fork_analysis(source, new, method='DE', niter=1, async_=False, monitor=False)

    recipe = json.load(open(os.path.join(new, "optimized", "recipe.json")))
    assert recipe['forked_from'] == os.path.abspath(source)
    assert recipe['seeded_from'].startswith("best of analysis-A")
    assert recipe['analysis_folder_name'] == "analysis-E" and recipe['note'] == "forked from analysis-A"
    np.testing.assert_allclose(recipe['seed_params'], src.result._rigorous_params)

    status = molass.analysis_status(new)
    assert status.start_fv == pytest.approx(src.result.fv, abs=1e-3)       # job 000 started from the seed
    assert "seeded from: best of analysis-A" in status.summary()
    assert status.jobs[0].first_fv == pytest.approx(src.result.fv, abs=1e-3)


@pytest.mark.slow
def test_a_source_the_caller_already_holds_is_not_rebuilt(finished, monkeypatch):
    """The GUI's result view has the decomposition, the trimmed data and the recipe: fork_source loads only the
    result of a job, and the plan is the same as from load_analysis."""
    from molass.Rigorous.ForkAnalysis import fork_source
    source, folder = finished
    loaded = molass.load_analysis(source)
    held = fork_source(source, loaded.decomp, loaded.trimmed, loaded.recipe)
    assert held.jobid == loaded.jobid and held.fv == pytest.approx(loaded.fv, abs=1e-3)
    assert held.result._rigorous_params is not None

    import molass.Rigorous.AnalysisFolder as analysis_folder_module
    monkeypatch.setattr(analysis_folder_module, "load_analysis",
                        lambda *a, **k: pytest.fail("the source was rebuilt although it was given"))
    plan = molass.fork_analysis(source, os.path.join(folder, "analysis-F"), dry_run=True, info=held)
    np.testing.assert_allclose(plan.seed_params, loaded.result._rigorous_params)
    assert plan.seed == 'best' and plan.info is held
    plan = molass.fork_analysis(source, os.path.join(folder, "analysis-G"), model="lkm", match_curves=True,
                                dry_run=True, info=held)
    assert plan.seed == 'converted' and plan.model == 'lkm'


def test_fork_source_without_a_completed_job_raises(tiny, tmp_path):
    from molass.Rigorous.CurrentStateUtils import NoCompletedJobError
    from molass.Rigorous.ForkAnalysis import fork_source
    trimmed, decomp = tiny
    folder = str(tmp_path / "empty")
    os.makedirs(os.path.join(folder, "optimized", "jobs"))
    with pytest.raises(NoCompletedJobError):
        fork_source(folder, decomp, trimmed, {})
