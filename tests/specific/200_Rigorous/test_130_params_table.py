"""Test molass.Rigorous.ParamsTable -- model-agnostic "Show Parameters" data extractor.

Promoted from molass-researcher/experiments/34_ssd_rigorous_gui/34k_show_parameters_design.ipynb,
where it was validated against EGH, SDM, CEDM, LKM and GRM (SAMPLE1).
"""
import pytest
import pandas as pd
from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD
from molass.Rigorous import build_params_table


@pytest.fixture(scope="module")
def base_decomp():
    ssd = SSD(SAMPLE1)
    trimmed = ssd.trimmed_copy()
    corrected = trimmed.corrected_copy()
    decomp = corrected.quick_decomposition(num_components=3)
    decomp.get_rg_curve()  # cache once; propagates to upgrade()'d children via _parent
    return decomp, trimmed


def _score_for(base_decomp, model):
    decomp, trimmed = base_decomp
    target = decomp if model == 'egh' else decomp.upgrade(model)
    return target.score(trimmed_ssd=trimmed)


@pytest.mark.parametrize("model", ["egh", "sdm", "cedm", "lkm", "grm"])
def test_build_params_table_returns_dataframe(base_decomp, model):
    score = _score_for(base_decomp, model)
    df = build_params_table(score.optimizer, score.init_params)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["section", "label", "component", "value"]
    assert len(df) > 0
    assert not df["section"].isna().any()


@pytest.mark.parametrize("model", ["egh", "sdm", "cedm", "lkm", "grm"])
def test_all_components_present_in_xr_rows(base_decomp, model):
    """Regression guard for the 1D xr_params bug: all 3 components must appear, not just 1."""
    score = _score_for(base_decomp, model)
    df = build_params_table(score.optimizer, score.init_params)

    xr_rows = df[df["section"] == "xr"]
    components = set(xr_rows["component"].dropna().unique())
    assert components == {1, 2, 3}


def test_cedm_xr_labels_not_egh_labels(base_decomp):
    """Regression guard: CEDM's [a, b, c_inj] must not be mislabeled with EGH names."""
    score = _score_for(base_decomp, "cedm")
    df = build_params_table(score.optimizer, score.init_params)

    xr_labels = set(df[df["section"] == "xr"]["label"].unique())
    assert xr_labels == {"a", "b", "c_inj", "rg"}
    assert "mu (tR)" not in xr_labels


def test_unsupported_model_raises(base_decomp):
    decomp, _ = base_decomp
    score = decomp.score(trimmed_ssd=base_decomp[1])

    class _FakeOptimizer:
        def split_params_simple(self, params):
            return score.optimizer.split_params_simple(params)

        def get_model_name(self):
            return "NEDM"

        n_components = score.optimizer.n_components

    with pytest.raises(ValueError, match="Unsupported model_name"):
        build_params_table(_FakeOptimizer(), score.init_params)
