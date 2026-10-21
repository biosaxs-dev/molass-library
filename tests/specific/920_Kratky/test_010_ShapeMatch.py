"""
Test Kratky.ShapeMatch and Decomposition.get_kratky_shape_match()/get_lrf_residual()/
plot_kratky_shape_match(). See molass-researcher/experiments/41_smoothing_kratky_plot/
41a-41e for the investigation this feature is based on.
"""
import numpy as np
import pytest
from molass.Testing import control_matplotlib_plot

decomp_baseline = None
decomp_underfit = None


@pytest.mark.order(1)
def test_010_setup():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    global decomp_baseline, decomp_underfit

    corrected = SSD(SAMPLE1).trimmed_copy().corrected_copy()
    decomp_baseline = corrected.quick_decomposition(num_components=3)
    decomp_underfit = corrected.quick_decomposition(num_components=2)
    assert decomp_baseline is not None
    assert decomp_underfit is not None


@pytest.mark.order(2)
def test_020_get_lrf_residual():
    residual_baseline = decomp_baseline.get_lrf_residual()
    residual_underfit = decomp_underfit.get_lrf_residual()

    assert isinstance(residual_baseline, float)
    assert residual_baseline >= 0
    # Under-fitting (merging two real components into one) should reliably
    # produce a worse (higher) reconstruction residual than the correct
    # baseline -- confirmed empirically in experiment 41c.
    assert residual_underfit > residual_baseline


@pytest.mark.order(3)
def test_030_get_kratky_shape_match_baseline():
    result = decomp_baseline.get_kratky_shape_match()

    assert result.score_matrix.shape == (3, len(result.shape_names))
    assert len(result.categories) == 3
    assert len(result.peak_qrgs) == 3
    # SAMPLE1's baseline components are all near-globular (Rg 24-36 A);
    # peaks should land close to sqrt(3) and be classified as compact.
    for category in result.categories:
        assert category == "compact / globular"
    # Row-normalized scores should sum to ~1 for every valid row.
    row_sums = np.nansum(result.score_matrix, axis=1)
    np.testing.assert_allclose(row_sums, 1.0, atol=1e-6)
    assert np.all(np.isfinite(result.best_raw_scores))
    assert np.all((np.asarray(result.best_raw_scores) > 0) & (np.asarray(result.best_raw_scores) <= 1))
    # Cached -- second call returns the same object without recomputing.
    assert decomp_baseline.get_kratky_shape_match() is result


@pytest.mark.order(4)
def test_040_get_kratky_shape_match_underfit_runs_without_error():
    # Under-fit (n=2) should not crash even though a real species got merged;
    # this is exactly the case where shape category alone is known (41c) to
    # look unremarkable despite the decomposition being wrong -- the point of
    # pairing this with get_lrf_residual(), not a claim this test catches it.
    result = decomp_underfit.get_kratky_shape_match()
    assert result.score_matrix.shape == (2, len(result.shape_names))


@pytest.mark.order(5)
@control_matplotlib_plot
def test_050_plot_kratky_shape_match():
    plot_result = decomp_baseline.plot_kratky_shape_match()
    assert plot_result.fig is not None
    # heatmap Axes is returned even though the figure also has the shape-key row
    assert plot_result.axes.get_title() == "Component x model-shape match score"


@pytest.mark.order(6)
@control_matplotlib_plot
def test_060_plot_kratky_shape_match_without_shape_key():
    plot_result = decomp_baseline.plot_kratky_shape_match(show_shape_key=False)
    assert plot_result.fig is not None


@pytest.mark.order(7)
def test_070_shape_key_image_is_cached():
    from molass.Kratky.ShapeKey import get_shape_key_image

    image_1 = get_shape_key_image()
    image_2 = get_shape_key_image()
    assert image_1.ndim == 3 and image_1.shape[2] == 4  # RGBA
    assert image_1 is image_2  # cached -- same object, not recomputed


class _FakeGuinier:
    def __init__(self, Rg, Iz):
        self.Rg, self.Iz = Rg, Iz


def _synthetic_match(P_fn, rg, noise, seed=0):
    from molass.Kratky.ShapeMatch import compute_shape_match_scores
    qv = np.linspace(0.004, 15/rg, 220)
    P = P_fn(qv*rg)
    P = P*(1 + noise*(1 + (qv*rg/3)**2)*np.random.default_rng(seed).standard_normal(len(qv)))
    return compute_shape_match_scores(qv, P[:, None], [_FakeGuinier(rg, 1.0)])


@pytest.mark.order(8)
def test_080_library_names_and_chain_flag():
    from molass.Kratky.ShapeLibrary import get_model_shapes

    specs = get_model_shapes()
    names = [spec.name for spec in specs]
    assert names == ["sphere",
                     "ellipsoid (eps=2)", "ellipsoid (eps=3)", "ellipsoid (eps=4)", "ellipsoid (eps=6)",
                     "cylinder (L/R=3)", "cylinder (L/R=6)", "cylinder (L/R=10)",
                     "Gaussian chain"]
    assert [spec.name for spec in specs if spec.is_chain] == ["Gaussian chain"]


@pytest.mark.order(9)
def test_090_chain_gating_for_peaked_curve():
    from molass.Kratky.FormFactors import ellipsoid_P, ellipsoid_Rg

    # a prolate ellipsoid has a clear Kratky peak far above sqrt(3); the chain must not win
    R, eps = 40.0, 5.0
    rg = ellipsoid_Rg(R, eps)
    result = _synthetic_match(lambda qrg: ellipsoid_P(qrg/rg, R, eps), rg, noise=0.003)
    top = result.shape_names[int(np.argmax(result.score_matrix[0]))]
    assert top != "Gaussian chain"
    assert 0.0 < result.best_raw_scores[0] <= 1.0


@pytest.mark.order(10)
def test_100_chain_still_matches_true_chain():
    from molass.Kratky.FormFactors import gaussian_chain_P

    rg = 60.0
    result = _synthetic_match(lambda qrg: gaussian_chain_P(qrg/rg, rg), rg, noise=0.003)
    top = result.shape_names[int(np.argmax(result.score_matrix[0]))]
    assert top == "Gaussian chain"


def _dblclick(fig, x, y):
    from matplotlib.backend_bases import MouseEvent
    event = MouseEvent("button_press_event", fig.canvas, x, y, button=1, dblclick=True)
    fig.canvas.callbacks.process("button_press_event", event)


@pytest.mark.order(11)
@control_matplotlib_plot
def test_110_plot_kratky_overlay():
    from molass.Kratky.ShapeMatch import plot_kratky_overlay
    from molass.Kratky.FormFactors import ellipsoid_P, ellipsoid_Rg

    R, eps = 40.0, 4.0
    rg = ellipsoid_Rg(R, eps)
    result = _synthetic_match(lambda qrg: ellipsoid_P(qrg/rg, R, eps), rg, noise=0.003)
    one = plot_kratky_overlay(result, 0, shapes=3)
    assert len(one.fig.axes) == 2  # overlay + residual
    assert len(one.axes.get_lines()) >= 3
    every = plot_kratky_overlay(result, 0, shapes=None, residual=False)
    assert len(every.fig.axes) == 1
    # redrawing into an existing figure reuses it
    again = plot_kratky_overlay(result, 0, shapes=[1, 2], fig=one.fig)
    assert again.fig is one.fig


@pytest.mark.order(13)
def test_130_kratky_descriptors():
    from molass.Kratky.ShapeMatch import kratky_descriptors

    x = np.linspace(0.4, 10, 220)
    noise = 0.01*np.random.default_rng(0).standard_normal(len(x))
    two_lobe = 1.8*np.exp(-((x - 3.2)/1.3)**2) + 0.55*np.exp(-((x - 8.0)/1.1)**2) + 0.35*np.exp(-x/6) + noise
    one_peak = 1.5*np.exp(-((x - 2.5)/1.3)**2) + 0.2 + noise
    monotone = 1.0 - np.exp(-x/2)
    d2 = kratky_descriptors(x, two_lobe)
    d1 = kratky_descriptors(x, one_peak)
    assert abs(d2["peak_qrg"] - 3.2) < 0.3
    assert d2["hump_prominence"] > 0.1       # the second lobe is a clear hump
    assert d1["hump_prominence"] == 0.0      # a single peak has none
    assert d1["tail_ratio"] < d2["tail_ratio"] or np.isnan(d2["tail_ratio"])
    assert kratky_descriptors(x, monotone) is None   # no interior peak


@pytest.mark.order(14)
@control_matplotlib_plot
def test_140_plot_kratky_series():
    result = decomp_baseline.get_kratky_shape_match()
    assert len(result.descriptors) == 3
    assert all(d is not None for d in result.descriptors)
    plot_result = decomp_baseline.plot_kratky_series()
    assert len(plot_result.fig.axes) == 2
    # redraw into an existing figure reuses it
    again = decomp_baseline.plot_kratky_series(fig=plot_result.fig)
    assert again.fig is plot_result.fig


@pytest.mark.order(12)
@control_matplotlib_plot
def test_120_double_click_opens_overlay():
    from molass.Kratky.ShapeMatch import plot_shape_match
    from molass.Kratky.FormFactors import ellipsoid_P, ellipsoid_Rg

    R, eps = 40.0, 4.0
    rg = ellipsoid_Rg(R, eps)
    result = _synthetic_match(lambda qrg: ellipsoid_P(qrg/rg, R, eps), rg, noise=0.003)

    calls = []
    plot_result = plot_shape_match(result, on_dblclick=lambda *args: calls.append(args))
    fig, ax = plot_result.fig, plot_result.axes
    fig.canvas.draw()

    x, y = ax.transData.transform((3, 0))
    _dblclick(fig, x, y)  # cell (component 0, shape 3)
    assert len(calls) == 1 and calls[0][1:] == (0, 3)

    label = ax.get_yticklabels()[0]
    bbox = label.get_window_extent(fig.canvas.get_renderer())
    _dblclick(fig, (bbox.x0 + bbox.x1)/2, (bbox.y0 + bbox.y1)/2)  # row label -> all shapes
    assert calls[-1][1:] == (0, None)

    _dblclick(fig, 1, 1)  # empty corner of the figure
    assert len(calls) == 2

    # interactive=False connects nothing
    quiet = plot_shape_match(result, interactive=False, on_dblclick=lambda *args: calls.append(args))
    quiet.fig.canvas.draw()
    x, y = quiet.axes.transData.transform((3, 0))
    _dblclick(quiet.fig, x, y)
    assert len(calls) == 2
