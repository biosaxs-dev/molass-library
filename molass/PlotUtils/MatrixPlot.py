"""
    PlotUtils.MatrixPlot.py

    Copyright (c) 2025, SAXS Team, KEK-PF
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
    cmap = kwargs.get('cmap', None)
    if cmap is None:
        kwargs['cmap'] = 'coolwarm'
    ax.plot_surface(xx, yy, zz, **kwargs)

def contour_plot(ax, M, x=None, y=None, **kwargs):
    xx, yy, zz = compute_3d_xyz(M, x, y)
    ax.contour(xx, yy, zz, **kwargs)