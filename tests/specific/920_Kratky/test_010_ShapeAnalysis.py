"""
Test Kratky.ShapeAnalysis and Decomposition.get_shape_analysis()/get_lrf_residual()/
plot_shape_analysis(). See molass-researcher/experiments/41_smoothing_kratky_plot/
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
def test_030_get_shape_analysis_baseline():
    result = decomp_baseline.get_shape_analysis()

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
    # Cached -- second call returns the same object without recomputing.
    assert decomp_baseline.get_shape_analysis() is result


@pytest.mark.order(4)
def test_040_get_shape_analysis_underfit_runs_without_error():
    # Under-fit (n=2) should not crash even though a real species got merged;
    # this is exactly the case where shape category alone is known (41c) to
    # look unremarkable despite the decomposition being wrong -- the point of
    # pairing this with get_lrf_residual(), not a claim this test catches it.
    result = decomp_underfit.get_shape_analysis()
    assert result.score_matrix.shape == (2, len(result.shape_names))


@pytest.mark.order(5)
@control_matplotlib_plot
def test_050_plot_shape_analysis():
    plot_result = decomp_baseline.plot_shape_analysis()
    assert plot_result.fig is not None
    # heatmap Axes is returned even though the figure also has the shape-key row
    assert plot_result.axes.get_title() == "Component x model-shape match score"


@pytest.mark.order(6)
@control_matplotlib_plot
def test_060_plot_shape_analysis_without_shape_key():
    plot_result = decomp_baseline.plot_shape_analysis(show_shape_key=False)
    assert plot_result.fig is not None


@pytest.mark.order(7)
def test_070_shape_key_image_is_cached():
    from molass.Kratky.ShapeKey import get_shape_key_image

    image_1 = get_shape_key_image()
    image_2 = get_shape_key_image()
    assert image_1.ndim == 3 and image_1.shape[2] == 4  # RGBA
    assert image_1 is image_2  # cached -- same object, not recomputed
