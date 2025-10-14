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