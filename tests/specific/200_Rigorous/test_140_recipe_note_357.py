"""A note stored in recipe.json and the analysis folder name at creation (molass-library#357)."""
import json
import os

import pytest

from molass.Rigorous.AnalysisFolder import AnalysisInfo
from molass.Rigorous.RigorousImplement import with_provenance


def _write_recipe(folder, recipe):
    os.makedirs(os.path.join(folder, "optimized"))
    with open(os.path.join(folder, "optimized", "recipe.json"), "w") as f:
        json.dump(recipe, f)


def test_note_and_folder_name_are_added(tmp_path):
    folder = str(tmp_path / "analysis-001")
    out = with_provenance({"model": "egh"}, folder, "Q2 rank-1 EGH, SAMPLE3")
    assert out["note"] == "Q2 rank-1 EGH, SAMPLE3"
    assert out["analysis_folder_name"] == "analysis-001"
    assert out["model"] == "egh"


def test_no_note_adds_only_the_folder_name(tmp_path):
    out = with_provenance({"model": "egh"}, str(tmp_path / "a"), None)
    assert "note" not in out and out["analysis_folder_name"] == "a"


def test_a_continued_folder_keeps_the_earlier_note_and_name(tmp_path):
    folder = str(tmp_path / "renamed")
    _write_recipe(folder, {"note": "first run", "analysis_folder_name": "analysis-001"})
    out = with_provenance({"model": "egh"}, folder, None)
    assert out["note"] == "first run" and out["analysis_folder_name"] == "analysis-001"


def test_a_new_note_replaces_the_earlier_one(tmp_path):
    folder = str(tmp_path / "f")
    _write_recipe(folder, {"note": "first run", "analysis_folder_name": "f"})
    assert with_provenance({}, folder, "second thought")["note"] == "second thought"


def test_a_recipe_that_already_has_them_is_not_overridden_by_the_folder(tmp_path):
    out = with_provenance({"note": "from the GUI", "analysis_folder_name": "gui-made"}, str(tmp_path / "x"), None)
    assert out["note"] == "from the GUI" and out["analysis_folder_name"] == "gui-made"


def _info(folder, recipe):
    return AnalysisInfo(folder, None, None, None, None, None, recipe, [], None)


def test_summary_shows_the_note_and_a_renamed_folder(tmp_path):
    info = _info(str(tmp_path / "Q2" / "analysis-rank1-EGH"),
                 dict(model="egh", note="Q2 rank-1 EGH, SAMPLE3", analysis_folder_name="analysis-003"))
    assert info.note == "Q2 rank-1 EGH, SAMPLE3"
    assert info.moved_from == "analysis-003"
    text = info.summary()
    assert "note: Q2 rank-1 EGH, SAMPLE3" in text
    assert "created as: analysis-003 (the folder was renamed or moved)" in text


def test_summary_of_an_old_recipe_has_neither(tmp_path):
    info = _info(str(tmp_path / "analysis-001"), dict(model="egh"))
    assert info.note is None and info.moved_from is None
    assert "note:" not in info.summary() and "created as" not in info.summary()


def test_optimize_rigorously_accepts_and_documents_note():
    import inspect
    from molass.LowRank.Decomposition import Decomposition
    from molass.Rigorous.RigorousImplement import make_rigorous_decomposition_impl
    assert "note" in inspect.signature(Decomposition.optimize_rigorously).parameters
    assert "note" in inspect.signature(make_rigorous_decomposition_impl).parameters
    assert "recipe.json" in Decomposition.optimize_rigorously.__doc__.split("note : ")[1]
