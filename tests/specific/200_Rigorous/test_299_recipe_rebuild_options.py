"""
molass-library#299: rebuilding a decomposition from recipe.json must use the recorded
options, not whatever the library default is today.
"""
import json
import os


class _Fake:
    seen = None

    def __init__(self, folder, **kwargs):
        pass

    def trimmed_copy(self, **kwargs):
        return self

    def corrected_copy(self, **kwargs):
        return self

    def quick_decomposition(self, **kwargs):
        _Fake.seen = kwargs
        return object()


def _rebuild(tmp_path, monkeypatch, recipe):
    import molass.DataObjects
    from molass.Rigorous.RecipeRunner import rebuild_decomposition_from_recipe

    monkeypatch.setattr(molass.DataObjects, 'SecSaxsData', _Fake)
    opt = tmp_path / "optimized"
    job = opt / "jobs" / "000"
    job.mkdir(parents=True)
    (job / "in_folder.txt").write_text(str(tmp_path))
    (opt / "recipe.json").write_text(json.dumps(recipe))
    _Fake.seen = None
    rebuild_decomposition_from_recipe(str(tmp_path))
    return _Fake.seen


def test_legacy_recipe_keeps_old_behaviour(tmp_path, monkeypatch):
    """A recipe without molass_version predates the Rg-order term (#295): rebuild without it."""
    seen = _rebuild(tmp_path, monkeypatch, {"num_components": 3, "decomp_params": {"proportions": [1, 2, 1]}})
    assert seen['rg_order_weight'] == 0


def test_recorded_weight_is_used(tmp_path, monkeypatch):
    recipe = {"num_components": 3, "molass_version": "1.1.4",
              "decomp_params": {"proportions": [1, 2, 1], "rg_order_weight": 0.3}}
    assert _rebuild(tmp_path, monkeypatch, recipe)['rg_order_weight'] == 0.3


def test_versioned_recipe_without_weight_uses_current_default(tmp_path, monkeypatch):
    recipe = {"num_components": 3, "molass_version": "1.1.4", "decomp_params": {"proportions": [1, 2, 1]}}
    assert 'rg_order_weight' not in _rebuild(tmp_path, monkeypatch, recipe)


def test_non_proportional_legacy_recipe_untouched(tmp_path, monkeypatch):
    seen = _rebuild(tmp_path, monkeypatch, {"num_components": 2, "decomp_params": {"xr_peakpositions": [500, 600]}})
    assert 'rg_order_weight' not in seen
