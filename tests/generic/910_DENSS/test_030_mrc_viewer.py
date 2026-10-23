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

def _heading_texts(fig):
    return [t.get_text() for t in fig.texts if t.get_text()]

def test_13_three_panel_headings_are_consistent_and_centred(mrc_path):
    fig = make_mrc_figure(mrc_path, level=0.2)
    FigureCanvasAgg(fig)
    fig.canvas.draw()
    bold = [t for t in fig.texts if t.get_fontweight() in ("bold", 700)]
    assert [t.get_text() for t in bold][:2] == ["3D view: isosurface", "Central slices"]
    assert bold[2].get_text().startswith("Density of the")
    assert len({t.get_fontsize() for t in bold}) == 1            # one heading style
    notes = [t for t in fig.texts if t.get_color() == "dimgray"]
    assert len(notes) == 3 and len({t.get_fontsize() for t in notes}) == 1
    # each heading is centred over its own panel
    ax3d = [a for a in fig.axes if a.name == "3d"][0]
    hist = [a for a in fig.axes if a.get_legend() is not None][0]
    slices = _slice_axes(fig)
    span = (min(a.get_position().x0 for a in slices), max(a.get_position().x1 for a in slices))
    centres = [t.get_position()[0] for t in bold]
    for c, (x0, x1) in zip(centres, ((ax3d.get_position().x0, ax3d.get_position().x1), (0.0, 1.0), (hist.get_position().x0, hist.get_position().x1))):
        if x1 - x0 < 1.0:
            assert abs(c - (x0 + x1) / 2) < 0.02
    assert span[0] < centres[1] < span[1]
    # the first two headings share one row; the histogram heading sits above its own panel
    assert bold[0].get_position()[1] == bold[1].get_position()[1]
    assert bold[2].get_position()[1] > hist.get_position().y1

def test_14_colorbar_spans_the_right_column(mrc_path):
    fig = make_mrc_figure(mrc_path, level=0.2)
    FigureCanvasAgg(fig)
    fig.canvas.draw()
    cbar = [a for a in fig.axes if a.get_ylabel() == "Density"][0].get_position()
    hist = [a for a in fig.axes if a.get_legend() is not None][0].get_position()
    top = max(a.get_position().y1 for a in _slice_axes(fig))
    assert cbar.y0 == pytest.approx(hist.y0, abs=1e-6)
    assert cbar.y1 >= top - 1e-6

def test_09_central_slices_are_three_labelled_panels(mrc_path):
    fig = make_mrc_figure(mrc_path, level=0.2)
    FigureCanvasAgg(fig)
    axes = _slice_axes(fig)
    assert [a.get_title() for a in axes] == ["yz plane", "xz plane", "xy plane"]
    for a in axes:
        assert a.get_xlabel().endswith("(\u00c5)") and a.get_ylabel().endswith("(\u00c5)")
        assert len(a.images) == 1
        assert len(a.collections) >= 1      # the threshold contour
    assert len(fig.legends) == 0
    texts = _heading_texts(fig)
    assert any(t.startswith("Central slices") for t in texts)
    assert any("threshold 0.2" in t for t in texts)
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
    assert len(fig.legends) == 0
    assert any("threshold %.3g" % state["level"] in t for t in _heading_texts(fig))
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

def test_12_colorbar_labels_stay_inside_the_figure(tmp_path):
    # a small maximum density gives wide tick labels like 0.0175 (the DENSS case)
    n = 24
    g = np.indices((n, n, n)).astype(float) - n / 2
    rho = 0.022 * np.exp(-((g[0] / 5) ** 2 + (g[1] / 3) ** 2 + (g[2] / 3) ** 2))
    path = tmp_path / "faint.mrc"
    with mrcfile.new(str(path)) as mrc:
        mrc.set_data(rho.astype(np.float32))
        mrc.voxel_size = 4.0
    from matplotlib.figure import Figure
    fig = make_mrc_figure(str(path), level=3e-5, fig=Figure(figsize=(12, 5.5)))
    FigureCanvasAgg(fig)
    fig.canvas.draw()
    cbax = [a for a in fig.axes if a.get_ylabel() == "Density"][0]
    right = cbax.get_tightbbox(fig.canvas.get_renderer()).x1
    assert right <= fig.bbox.x1, "colorbar labels are clipped at the right edge"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
