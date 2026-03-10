"""
    PlotUtils.MatrixPlot.py
"""
import numpy as np

def compute_3d_xyz(M, x=None, y=None):
    x_size = M.shape[0]
    n = max(1, x_size//200)
    i = np.arange(0, x_size, n)
    j = np.arange(M.shape[1])
    ii, jj = np.meshgrid(i, j)
    zz = M[ii, jj]
    if x is None:
        x_ = i
    else:
        x_ = x[slice(0, len(x), n)]
    if y is None:
        y = j
    xx, yy = np.meshgrid(x_, y)
    return xx, yy, zz

def simple_plot_3d(ax, M, x=None, y=None, **kwargs):
    """Plot M as a 3D surface on a provided 3D axes.

    The caller is responsible for creating the figure and 3D axes:

        fig, ax = plt.subplots(subplot_kw={'projection': '3d'})
        simple_plot_3d(ax, M, x=q_values, y=frame_numbers)

    Parameters
    ----------
    ax : mpl_toolkits.mplot3d.Axes3D
        An existing 3D axes to plot into.
    M : 2D array-like, shape (n_x, n_y)
        The matrix to render as a surface.
    x : array-like, optional
        Values for the first axis (rows of M). Defaults to integer indices.
    y : array-like, optional
        Values for the second axis (columns of M). Defaults to integer indices.
    **kwargs
        Additional keyword arguments passed to ``ax.plot_surface()``, plus:
        ``view_init`` (dict) — passed to ``ax.view_init()``;
        ``colorbar`` (bool) — add a colorbar if True;
        ``view_arrows`` (bool) — overlay view-direction arrows if True.
    """
    xx, yy, zz = compute_3d_xyz(M, x, y)
    view_init_kwargs = kwargs.pop('view_init', {})
    view_arrows = kwargs.pop('view_arrows', False)
    colorbar = kwargs.pop('colorbar', False)
    sfp = ax.plot_surface(xx, yy, zz, **kwargs)
    if colorbar:
        ax.get_figure().colorbar(sfp, ax=ax)
    if view_arrows:
        from importlib import reload
        import molass.PlotUtils.ViewArrows
        reload(molass.PlotUtils.ViewArrows)
        from molass.PlotUtils.ViewArrows import plot_view_arrows
        plot_view_arrows(ax)
    ax.view_init(**view_init_kwargs)

def contour_plot(ax, M, x=None, y=None, **kwargs):
    xx, yy, zz = compute_3d_xyz(M, x, y)
    ax.contour(xx, yy, zz, **kwargs)