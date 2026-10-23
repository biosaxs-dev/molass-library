"""
    test MrcViewer
"""
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used

import numpy as np
import pytest

mrcfile = pytest.importorskip("mrcfile")
pytest.importorskip("skimage")

from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from molass.SAXS.MrcViewer import make_mrc_figure

@pytest.fixture(scope="module")
def mrc_path(tmp_path_factory):
    n = 24
    g = np.indices((n, n, n)).astype(float) - n / 2
    # an elongated blob, so that the slices and the isosurface are not degenerate
    rho = np.exp(-((g[0] / 5) ** 2 + (g[1] / 3) ** 2 + (g[2] / 3) ** 2))
    path = tmp_path_factory.mktemp("mrc") / "blob.mrc"
    with mrcfile.new(str(path)) as mrc:
        mrc.set_data(rho.astype(np.float32))
        mrc.voxel_size = 4.0
    return str(path)

def test_01_make_figure_without_pyplot(mrc_path):
    import matplotlib.pyplot as plt
    before = plt.get_fignums()
    fig = make_mrc_figure(mrc_path, level=0.2)
    assert plt.get_fignums() == before, "make_mrc_figure must not create pyplot figures"
    state, radio, check, slider, ax = fig._mrc_viewer_state
    assert state["view"] == "Isosurface"
    assert state["poly"].get_visible() and not state["sc"].get_visible()

def test_02_switch_view(mrc_path):
    fig = make_mrc_figure(mrc_path, level=0.2)
    FigureCanvasAgg(fig)        # the GUI replaces the canvas after construction
    state, radio, check, slider, ax = fig._mrc_viewer_state
    radio.set_active(1)
    assert state["view"] == "Voxel scatter"
    assert state["sc"].get_visible() and not state["poly"].get_visible()
    radio.set_active(0)
    assert state["poly"].get_visible() and not state["sc"].get_visible()
    fig.canvas.draw()

def test_03_coarse_mesh_while_dragging(mrc_path):
    fig = make_mrc_figure(mrc_path, level=0.2)
    FigureCanvasAgg(fig)
    state, radio, check, slider, ax = fig._mrc_viewer_state
    x, y = (ax.bbox.x0 + ax.bbox.x1) / 2, (ax.bbox.y0 + ax.bbox.y1) / 2   # away from the radio/check widgets

    def fire(name):
        fig.canvas.callbacks.process(name, MouseEvent(name, fig.canvas, x, y, button=1))

    fire("button_press_event")
    assert state["mode"] == "coarse"
    fire("button_release_event")
    assert state["mode"] == "fine"

def test_04_auto_rotate_toggle(mrc_path):
    fig = make_mrc_figure(mrc_path, level=0.2)
    FigureCanvasAgg(fig)
    state, radio, check, slider, ax = fig._mrc_viewer_state
    check.set_active(0)
    assert state["auto"] and state["mode"] == "coarse" and state["timer"] is not None
    check.set_active(0)
    assert not state["auto"] and state["mode"] == "fine"

def test_05_level_above_data_raises(mrc_path):
    with pytest.raises(ValueError):
        make_mrc_figure(mrc_path, level=10.0)

def _slider_event(fig, slider, name):
    ax = slider.ax
    x, y = (ax.bbox.x0 + ax.bbox.x1) / 2, (ax.bbox.y0 + ax.bbox.y1) / 2
    fig.canvas.callbacks.process(name, MouseEvent(name, fig.canvas, x, y, button=1))

def test_06_slider_changes_level_on_release(mrc_path):
    fig = make_mrc_figure(mrc_path, level=0.2)
    FigureCanvasAgg(fig)
    state, radio, check, slider, ax = fig._mrc_viewer_state
    old_poly, old_level = state["poly"], state["level"]
    _slider_event(fig, slider, "button_press_event")
    slider.set_val(-0.3)                                # (the press itself already moved the slider)
    assert state["poly"] is old_poly
    _slider_event(fig, slider, "button_release_event")
    assert state["poly"] is not old_poly
    assert state["level"] > old_level
    assert state["level"] == pytest.approx(10 ** slider.val * 1.0, rel=0.05)   # the blob peaks at 1.0
    fig.canvas.draw()

def test_07_slider_survives_scatter_view_and_auto_rotate(mrc_path):
    fig = make_mrc_figure(mrc_path, level=0.2)
    FigureCanvasAgg(fig)
    state, radio, check, slider, ax = fig._mrc_viewer_state
    radio.set_active(1)
    check.set_active(0)
    _slider_event(fig, slider, "button_press_event")
    slider.set_val(-3.0)
    _slider_event(fig, slider, "button_release_event")
    assert state["view"] == "Voxel scatter"
    assert state["sc"].get_visible() and not state["poly"].get_visible()
    assert state["mode"] == "coarse"        # auto-rotate is still on
    check.set_active(0)
    fig.canvas.draw()

@pytest.fixture(scope="module")
def spiky_mrc_path(tmp_path_factory):
    n = 24
    g = np.indices((n, n, n)).astype(float) - n / 2
    rho = np.exp(-((g[0] / 5) ** 2 + (g[1] / 3) ** 2 + (g[2] / 3) ** 2))
    rho[2, 2, 2] = 50.0         # an isolated spike that smoothing flattens below any useful level
    path = tmp_path_factory.mktemp("mrc") / "spiky.mrc"
    with mrcfile.new(str(path)) as mrc:
        mrc.set_data(rho.astype(np.float32))
        mrc.voxel_size = 4.0
    return str(path)

def test_08_slider_level_without_surface_is_rejected(spiky_mrc_path):
    fig = make_mrc_figure(spiky_mrc_path, level=0.2)
    FigureCanvasAgg(fig)
    state, radio, check, slider, ax = fig._mrc_viewer_state
    old_poly, old_level, old_value = state["poly"], state["level"], slider.val
    _slider_event(fig, slider, "button_press_event")
    slider.set_val(-0.3)                                # level 25: only the spike exceeds it
    _slider_event(fig, slider, "button_release_event")
    assert state["poly"] is old_poly and state["level"] == old_level
    assert slider.val == pytest.approx(old_value)
    fig.canvas.draw()

def _slice_axes(fig):
    return [a for a in fig.axes if a.get_title() in ("yz plane", "xz plane", "xy plane")]

def test_09_central_slices_are_three_labelled_panels(mrc_path):
    fig = make_mrc_figure(mrc_path, level=0.2)
    FigureCanvasAgg(fig)
    axes = _slice_axes(fig)
    assert [a.get_title() for a in axes] == ["yz plane", "xz plane", "xy plane"]
    for a in axes:
        assert a.get_xlabel().endswith("(\u00c5)") and a.get_ylabel().endswith("(\u00c5)")
        assert len(a.images) == 1
        assert len(a.collections) >= 1      # the threshold contour
    assert len(fig.legends) == 1 and "0.2" in fig.legends[0].get_texts()[0].get_text()
    hist = [a for a in fig.axes if a.get_legend() is not None]
    assert len(hist) == 1 and "threshold" in hist[0].get_legend().get_texts()[0].get_text()
    fig.canvas.draw()

def test_10_slice_legend_follows_level_slider(mrc_path):
    fig = make_mrc_figure(mrc_path, level=0.2)
    FigureCanvasAgg(fig)
    state, radio, check, slider, ax = fig._mrc_viewer_state
    _slider_event(fig, slider, "button_press_event")
    slider.set_val(-0.3)
    _slider_event(fig, slider, "button_release_event")
    assert len(fig.legends) == 1
    assert "%.3g" % state["level"] in fig.legends[0].get_texts()[0].get_text()
    assert len(_slice_axes(fig)) == 3
    fig.canvas.draw()

def test_11_density_colorbar_is_shared_in_both_views(mrc_path):
    fig = make_mrc_figure(mrc_path, level=0.2)
    FigureCanvasAgg(fig)
    state, radio, check, slider, ax = fig._mrc_viewer_state
    cbars = [a for a in fig.axes if a.get_ylabel() == "Density"]
    assert len(cbars) == 1
    for label in ("Isosurface", "Voxel scatter"):
        radio.set_active(0 if label == "Isosurface" else 1)
        assert cbars[0].get_visible()
    # the scatter and the slices use the same scale: 0 .. maximum density (1.0 for this blob)
    assert state["sc"].norm.vmin == 0 and state["sc"].norm.vmax == pytest.approx(1.0)
    for a in _slice_axes(fig):
        assert a.images[0].norm.vmin == 0 and a.images[0].norm.vmax == pytest.approx(1.0)
    # the isosurface is neutral lighting of one hue (blue > green > red), not the density colormap
    colors = np.asarray(state["poly"].get_facecolor())
    assert (colors[:, 2] > colors[:, 1]).all() and (colors[:, 1] > colors[:, 0]).all()
    fig.canvas.draw()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
