"""
Kratky.ShapeKey

A persistent, fixed "shape key" -- one representative icon per reference
shape in ``molass.Kratky.ShapeLibrary.get_model_shapes()``. The icons never
change per analysis (same design principle as a map/UI pictogram: generic
and unfittable by construction, so they can't be mistaken for a per-component
fitted result -- see ShapeAnalysis.py's module docstring), and their order
matches the match-score heatmap's columns exactly (both read from the same
shared library), so ``plot_shape_analysis()`` can align them 1:1.

Rendering several 3D surfaces is cheap (well under a second) but not free,
and a matplotlib Axes3D cannot be moved into another figure's layout. So the
panel is rendered once, rasterized to a plain RGBA image, and cached in
memory (functools.lru_cache) -- reused image, not reused Axes3D. This is
preferred over shipping a pre-baked PNG asset in the package: no binary asset
to keep in sync with the generation code below, only a one-time per-process
render cost.
"""
from functools import lru_cache
import numpy as np

from molass.Kratky.ShapeLibrary import get_model_shapes


def _set_equal_box(ax, extent, pad=1.15):
    e = extent*pad
    ax.set_xlim(-e, e); ax.set_ylim(-e, e); ax.set_zlim(-e, e)
    ax.set_box_aspect([1, 1, 1])
    ax.set_xticklabels([]); ax.set_yticklabels([]); ax.set_zticklabels([])


@lru_cache(maxsize=1)
def _render_shape_key_rgba():
    """Render one 3D icon per shape in get_model_shapes(), in the same order,
    as N equal-width panels. Cached for the lifetime of the process."""
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 (registers 3D projection)

    model_shapes = get_model_shapes()
    n = len(model_shapes)

    # No per-icon titles: the heatmap's xticklabels (same names, same order) already
    # label these columns, and titles this small only added clutter, not information.
    fig = plt.figure(figsize=(2.0*n, 2.0))
    for i, spec in enumerate(model_shapes):
        ax = fig.add_subplot(1, n, i+1, projection="3d")
        extent = spec.plot3d_fn(ax)
        _set_equal_box(ax, extent)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01, wspace=0.05)

    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    plt.close(fig)
    return rgba


def get_shape_key_image():
    """Return the fixed shape-key panel as an RGBA numpy array (H, W, 4),
    with one equal-width icon per :func:`molass.Kratky.ShapeLibrary.get_model_shapes`
    entry, in the same order -- suitable for ``Axes.imshow(..., aspect='auto')``
    stretched across the same column span as the match-score heatmap.
    Cached -- cheap after the first call in a process.

    Returns
    -------
    ndarray
    """
    return _render_shape_key_rgba()
