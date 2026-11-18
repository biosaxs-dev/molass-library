"""AI-friendliness fixes of molass-library#401 (progress_cb), #402 (reload only with debug), #404 (quiet_legacy in the
rigorous setup); real SAMPLE3 fit, no optimization run."""
import json
import warnings

import pytest

molass_data = pytest.importorskip("molass_data")


@pytest.fixture(scope="module")
def sample3():
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(molass_data.SAMPLE3)
    trimmed = ssd.trimmed_copy()
    return trimmed, trimmed.corrected_copy().quick_decomposition(num_components=1)


def _analysis_folder(tmp_path, recipe):
    folder = tmp_path / "analysis"
    job = folder / "optimized" / "jobs" / "000"
    job.mkdir(parents=True)
    (job / "in_folder.txt").write_text(molass_data.SAMPLE3)
    (folder / "optimized" / "recipe.json").write_text(json.dumps(recipe))
    return str(folder)


# --- #401 ---------------------------------------------------------------------------------------------------

def test_rebuild_reports_its_stages(sample3, tmp_path):
    from molass.Rigorous.RigorousImplement import build_pipeline_recipe
    from molass.Rigorous.RecipeRunner import rebuild_decomposition_from_recipe

    trimmed, decomp = sample3
    folder = _analysis_folder(tmp_path, build_pipeline_recipe(decomp, method='BH', niter=2, ssd=trimmed))
    calls = []
    rebuild_decomposition_from_recipe(folder, progress_cb=lambda stage, fraction: calls.append((stage, fraction)))
    assert [s for s, _ in calls] == ["Loading the data", "Trimming", "Correcting the baseline",
                                     "Quick decomposition", "Done"]
    fractions = [f for _, f in calls]
    assert fractions == sorted(fractions) and fractions[0] == 0 and fractions[-1] == 1


def test_load_analysis_and_fork_pass_the_progress_callback_on(tmp_path, monkeypatch):
    import molass
    from molass.Rigorous import RecipeRunner, AnalysisFolder
    from molass.Rigorous.ForkAnalysis import plan_fork

    seen = {}

    class Stop(Exception):
        pass

    def fake_rebuild(folder, in_folder=None, debug=False, progress_cb=None):
        seen['rebuild'] = progress_cb
        raise Stop

    def cb(stage, fraction):
        pass

    folder = _analysis_folder(tmp_path, {"model": "egh"})
    monkeypatch.setattr(RecipeRunner, "rebuild_decomposition_from_recipe", fake_rebuild)
    with pytest.raises(Stop):
        molass.load_analysis(folder, progress_cb=cb)
    assert seen['rebuild'] is cb

    seen.clear()
    with pytest.raises(Stop):
        plan_fork(folder, str(tmp_path / "fork"), progress_cb=cb)
    assert seen['rebuild'] is cb


# --- #402 ---------------------------------------------------------------------------------------------------

def _count_reloads(monkeypatch):
    import importlib
    import molass.LowRank.Decomposition as decomposition_module
    import molass.Rigorous.RigorousImplement as implement_module
    import molass.Rigorous.Score as score_module
    calls = []

    def counting_reload(module):
        if module.__name__.startswith("molass."):     # molass_legacy reloads its own modules: not what #402 is about
            calls.append(module.__name__)
        return module
    for mod in (importlib, decomposition_module, implement_module, score_module):
        monkeypatch.setattr(mod, "reload", counting_reload, raising=False)
    return calls


def test_the_rigorous_setup_does_not_reload_modules_without_debug(sample3, tmp_path, monkeypatch):
    trimmed, decomp = sample3
    calls = _count_reloads(monkeypatch)
    decomp.optimize_rigorously(trimmed_ssd=trimmed, analysis_folder=str(tmp_path / "dry"), dry_run=True)
    decomp.score(trimmed_ssd=trimmed)
    assert calls == []


def test_debug_still_reloads(sample3, tmp_path, monkeypatch):
    trimmed, decomp = sample3
    calls = _count_reloads(monkeypatch)
    decomp.optimize_rigorously(trimmed_ssd=trimmed, analysis_folder=str(tmp_path / "dry"), dry_run=True, debug=True)
    assert "molass.Rigorous.RigorousImplement" in calls


# --- #404 ---------------------------------------------------------------------------------------------------

def test_user_warnings_of_the_setup_survive_the_quiet_block_and_numerical_noise_does_not(sample3, monkeypatch):
    import molass.Rigorous.LegacyBridgeUtils as bridge
    trimmed, decomp = sample3

    class Stop(Exception):
        pass

    def noisy_prepare(*args, **kwargs):
        print("legacy trace")
        warnings.warn("invalid value encountered in divide", RuntimeWarning)
        warnings.warn("the seed has 5 values but 7 are needed", UserWarning)
        raise Stop

    monkeypatch.setattr(bridge, "prepare_rigorous_folders", noisy_prepare)      # survives, as there is no reload
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(Stop) as info:
            decomp.score(trimmed_ssd=trimmed)
    messages = [str(w.message) for w in caught]
    assert "the seed has 5 values but 7 are needed" in messages
    assert not any("invalid value" in m for m in messages)
    assert "legacy trace" in "\n".join(getattr(info.value, "__notes__", []))
