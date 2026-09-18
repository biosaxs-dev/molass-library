"""
Kratky.ShapeLibrary

Single source of truth for the fixed reference-shape library used by both
``ShapeAnalysis`` (match-score computation) and ``ShapeKey`` (icon rendering).

Keeping both consumers pointed at this one list -- same order, same names --
guarantees the shape-key icons and the match-score heatmap's columns always
correspond 1:1 by construction, rather than by two lists that happen to agree
today but could silently drift apart later.
"""
from collections import namedtuple
import numpy as np

from molass.Kratky.FormFactors import (
    sphere_F, sphere_Rg, ellipsoid_P, ellipsoid_Rg, cylinder_P, cylinder_Rg,
    gaussian_chain_P,
)

ShapeSpec = namedtuple("ShapeSpec", ["name", "Rg", "P_fn", "plot3d_fn"])

_R_REF = 40.0  # arbitrary reference length scale; only Rg (derived) matters for the Kratky curve


def _plot_sphere_3d(ax, R, color):
    u = np.linspace(0, 2*np.pi, 30)
    v = np.linspace(0, np.pi, 15)
    x = R*np.outer(np.cos(u), np.sin(v))
    y = R*np.outer(np.sin(u), np.sin(v))
    z = R*np.outer(np.ones_like(u), np.cos(v))
    ax.plot_surface(x, y, z, color=color, alpha=0.9, linewidth=0)
    return R


def _plot_ellipsoid_3d(ax, R, eps, color):
    u = np.linspace(0, 2*np.pi, 30)
    v = np.linspace(0, np.pi, 15)
    x = R*np.outer(np.cos(u), np.sin(v))
    y = R*np.outer(np.sin(u), np.sin(v))
    z = (eps*R)*np.outer(np.ones_like(u), np.cos(v))
    ax.plot_surface(x, y, z, color=color, alpha=0.9, linewidth=0)
    return max(R, eps*R)


def _plot_cylinder_3d(ax, R, L, color):
    theta = np.linspace(0, 2*np.pi, 30)
    z_line = np.linspace(-L/2, L/2, 2)
    theta_grid, z_grid = np.meshgrid(theta, z_line)
    x = R*np.cos(theta_grid)
    y = R*np.sin(theta_grid)
    ax.plot_surface(x, y, z_grid, color=color, alpha=0.9, linewidth=0)
    r_grid, theta_grid2 = np.meshgrid(np.linspace(0, R, 8), theta)
    xc, yc = r_grid*np.cos(theta_grid2), r_grid*np.sin(theta_grid2)
    for zc in (L/2, -L/2):
        ax.plot_surface(xc, yc, np.full_like(xc, zc), color=color, alpha=0.9, linewidth=0)
    return max(R, L/2)


def _plot_chain_3d(ax, Rg, color, n_segments=250, seed=1):
    rng = np.random.default_rng(seed)
    b = Rg*np.sqrt(6/n_segments)
    steps = rng.normal(size=(n_segments, 3))
    steps /= np.linalg.norm(steps, axis=1, keepdims=True)
    steps *= b
    path = np.cumsum(steps, axis=0)
    path -= path.mean(axis=0)
    ax.plot(path[:, 0], path[:, 1], path[:, 2], color=color, lw=1.3)
    return np.max(np.abs(path))


def get_model_shapes():
    """The canonical, fixed reference-shape library.

    Order here IS the column order in the match-score heatmap and the icon
    order in the shape key -- do not reorder without updating both consumers'
    expectations (neither hardcodes the order elsewhere, so reordering here
    is otherwise safe).

    Returns
    -------
    list of ShapeSpec
        Each has ``.name``, ``.Rg`` (exact, from the form factor's own
        Rg relation), ``.P_fn(qs)`` (form factor as a function of q), and
        ``.plot3d_fn(ax)`` (draws the 3D representative shape into ``ax``,
        returns its bounding extent).
    """
    cyl1_R, cyl1_L = 20.0, 60.0
    cyl2_R, cyl2_L = 20.0, 200.0
    return [
        ShapeSpec("sphere", sphere_Rg(_R_REF),
                  lambda qs: sphere_F(np.asarray(qs)*_R_REF)**2,
                  lambda ax: _plot_sphere_3d(ax, _R_REF, "C0")),
        ShapeSpec("ellipsoid (eps=2)", ellipsoid_Rg(_R_REF, 2.0),
                  lambda qs: ellipsoid_P(qs, _R_REF, 2.0),
                  lambda ax: _plot_ellipsoid_3d(ax, _R_REF, 2.0, "C1")),
        ShapeSpec("ellipsoid (eps=6)", ellipsoid_Rg(_R_REF, 6.0),
                  lambda qs: ellipsoid_P(qs, _R_REF, 6.0),
                  lambda ax: _plot_ellipsoid_3d(ax, _R_REF, 6.0, "C2")),
        ShapeSpec("cylinder (L/R=3)", cylinder_Rg(cyl1_R, cyl1_L),
                  lambda qs: cylinder_P(qs, cyl1_R, cyl1_L),
                  lambda ax: _plot_cylinder_3d(ax, cyl1_R, cyl1_L, "C3")),
        ShapeSpec("cylinder (L/R=10)", cylinder_Rg(cyl2_R, cyl2_L),
                  lambda qs: cylinder_P(qs, cyl2_R, cyl2_L),
                  lambda ax: _plot_cylinder_3d(ax, cyl2_R, cyl2_L, "C4")),
        ShapeSpec("Gaussian chain", _R_REF,
                  lambda qs: gaussian_chain_P(qs, _R_REF),
                  lambda ax: _plot_chain_3d(ax, _R_REF, "C5")),
    ]
