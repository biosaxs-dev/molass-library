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

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
