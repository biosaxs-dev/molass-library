"""
    Test issue #383: component.get_xy(), xr_peakpositions as a list, and the documented axes of plot_compact().
"""
import matplotlib
matplotlib.use("Agg")
import pytest
from molass import get_version
get_version(toml_only=True)
from molass.Testing import simulate_sample4_like


@pytest.fixture(scope="module")
def corrected():
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return simulate_sample4_like().trimmed_copy().corrected_copy()


def test_recommended_xr_peakpositions_is_a_list_of_ints(corrected):
    opts = corrected.recommend_decomposition_options()
    positions = opts['xr_peakpositions']
    assert isinstance(positions, list) and all(type(p) is int for p in positions)
    assert (opts.get('xr_peakpositions') or []) == positions       # no ambiguous truth value (an ndarray had one)
    corrected.quick_decomposition(**opts)                          # and accepted as it is


def test_components_have_get_xy(corrected):
    decomp = corrected.quick_decomposition(num_components=2)
    for comp in decomp.get_xr_components() + decomp.get_uv_components():
        x, y = comp.get_xy()
        ix, iy = comp.get_icurve().get_xy()
        assert (x == ix).all() and (y == iy).all()


def test_plot_compact_axes(corrected):
    result = corrected.plot_compact()
    xr, uv_spectrum, xr_spectrum = result.axes
    assert xr.get_xlabel() == "Frame Index for X-ray"
    assert uv_spectrum.get_xlabel() == "Wavelength (nm)"
    assert xr_spectrum.get_xlabel().startswith("Q")
    assert result.uv_ax is result.fig.axes[1] and result.uv_ax is not xr
    assert result.uv_ax.bbox.bounds == xr.bbox.bounds      # laid over the elution panel
    result.close()
