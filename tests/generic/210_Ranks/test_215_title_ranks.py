"""
The default figure title (``plot_components(title='auto')`` and friends) shows the XR ranks
only when some component has a rank other than 1 (the all-rank-1 default is unchanged).
Pure function of its arguments: no dataset needed.
"""
from molass.PlotUtils.DecompositionPlot import make_title_text


def test_default_title_has_no_ranks():
    base = make_title_text(None, "egh", "quick decomposition", dataset="SAMPLE3")
    assert base == "SAMPLE3 | model: EGH | method: quick decomposition"
    assert make_title_text(None, "egh", "quick decomposition", dataset="SAMPLE3", xr_ranks=None) == base
    assert make_title_text(None, "egh", "quick decomposition", dataset="SAMPLE3", xr_ranks=[1]) == base
    assert make_title_text(None, "egh", "quick decomposition", dataset="SAMPLE3", xr_ranks=[1, 1, 1]) == base


def test_title_shows_ranks_when_a_component_has_rank_2():
    title = make_title_text(None, "grm", "rigorous optimization (BH)", dataset="SAMPLE3", xr_ranks=[2])
    assert title == "SAMPLE3 | model: GRM | method: rigorous optimization (BH) | ranks: 2"
    title = make_title_text(None, "egh", None, dataset="SAMPLE1", xr_ranks=[1, 2, 1])
    assert title == "SAMPLE1 | model: EGH | ranks: 1,2,1"
