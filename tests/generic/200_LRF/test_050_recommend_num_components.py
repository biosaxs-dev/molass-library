"""
    Test issue #116: Decomposition.recommend_num_components()

    Verifies on SAMPLE1 (clean true positive at k=k_max) and Apo
    (degeneracy at k=2 -> recommend k=1).
"""
import os
import pytest
import pandas as pd
from molass import get_version
get_version(toml_only=True)
from molass.Global.Options import set_molass_options
from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD
from molass.LowRank.NumComponentsRecommender import Recommendation

set_molass_options(quiet=True)


@pytest.fixture(scope="module")
def sample1_decomp():
    ssd = SSD(SAMPLE1)
    corrected = ssd.trimmed_copy().corrected_copy()
    corrected.estimate_mapping()
    return corrected.quick_decomposition(num_components=2)


def test_recommend_returns_namedtuple(sample1_decomp):
    rec = sample1_decomp.recommend_num_components(k_max=2)
    assert isinstance(rec, Recommendation)
    assert isinstance(rec.metrics, pd.DataFrame)
    assert set(rec.metrics.columns) >= {
        "k", "residual", "cond_C", "max_cos", "amp_ratio",
        "flag_count", "status",
    }
    # k_max=2 -> rows for k=1 and k=2
    assert sorted(rec.metrics["k"].tolist()) == [1, 2]
    assert rec.recommended_k in (1, 2)
    assert rec.reason  # non-empty


def test_recommend_sample1_no_degeneracy(sample1_decomp):
    """SAMPLE1 has true k>=3; at k_max=3 no degeneracy should be detected."""
    rec = sample1_decomp.recommend_num_components(k_max=3)
    assert rec.recommended_k == 3
    assert "no degeneracy" in rec.reason.lower()
    # All three fits succeeded
    assert (rec.metrics["status"] == "ok").all()
    # Residual must be monotonically non-increasing as k grows
    res = rec.metrics.sort_values("k")["residual"].tolist()
    assert res[0] >= res[1] >= res[2]


APO_PATH = r"C:\Users\takahashi\Dropbox\MOLASS\DATA\20260305\Apo"


@pytest.mark.skipif(not os.path.isdir(APO_PATH),
                    reason="Apo dataset not available on this machine")
def test_recommend_apo_picks_one_component():
    """Apo is monodisperse; k=2 should be flagged degenerate (residual jumps
    or >=2 flags), recommendation must be k=1."""
    ssd = SSD(APO_PATH)
    corrected = ssd.trimmed_copy().corrected_copy()
    corrected.estimate_mapping()
    decomp = corrected.quick_decomposition(num_components=2)
    rec = decomp.recommend_num_components(k_max=2)
    assert rec.recommended_k == 1
    # Either residual went up or k=2 raised flags
    m = rec.metrics.sort_values("k").reset_index(drop=True)
    k1, k2 = m.iloc[0], m.iloc[1]
    assert (k2["residual"] > k1["residual"]) or (k2["flag_count"] >= 2)
