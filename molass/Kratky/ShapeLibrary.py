"""
Kratky.ShapeLibrary

Single source of truth for the fixed reference-shape library used by both
``ShapeMatch`` (match-score computation) and ``ShapeKey`` (icon rendering).

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

ShapeSpec = namedtuple("ShapeSpec", ["name", "Rg", "P_fn", "plot3d_fn", "is_chain"],
                       defaults=(False,))

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
        returns its bounding extent), and ``.is_chain`` (True for the
        flexible-chain reference, which has no Kratky peak).
    """
    cyl_R = 20.0
    ellipsoid_epss = (2.0, 3.0, 4.0, 6.0)
    cylinder_ratios = (3.0, 6.0, 10.0)

    specs = [
        ShapeSpec("sphere", sphere_Rg(_R_REF),
                  lambda qs: sphere_F(np.asarray(qs)*_R_REF)**2,
                  lambda ax: _plot_sphere_3d(ax, _R_REF, "C0")),
    ]
    for i, eps in enumerate(ellipsoid_epss):
        specs.append(ShapeSpec(f"ellipsoid (eps={eps:g})", ellipsoid_Rg(_R_REF, eps),
                               lambda qs, eps=eps: ellipsoid_P(qs, _R_REF, eps),
                               lambda ax, eps=eps, i=i: _plot_ellipsoid_3d(ax, _R_REF, eps, f"C{i+1}")))
    for i, ratio in enumerate(cylinder_ratios):
        L = cyl_R*ratio
        specs.append(ShapeSpec(f"cylinder (L/R={ratio:g})", cylinder_Rg(cyl_R, L),
                               lambda qs, L=L: cylinder_P(qs, cyl_R, L),
                               lambda ax, L=L, i=i: _plot_cylinder_3d(ax, cyl_R, L, f"C{i+5}")))
    specs.append(ShapeSpec("Gaussian chain", _R_REF,
                           lambda qs: gaussian_chain_P(qs, _R_REF),
                           lambda ax: _plot_chain_3d(ax, _R_REF, "C8"),
                           is_chain=True))
    return specs
