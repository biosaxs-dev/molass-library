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
    sphere_F, sphere_Rg, ellipsoid_P, ellipsoid_Rg, triaxial_P, triaxial_Rg, cylinder_P, cylinder_Rg,
    gaussian_chain_P, bead_assembly_P, bead_assembly_Rg,
)

ShapeSpec = namedtuple("ShapeSpec", ["name", "Rg", "P_fn", "plot3d_fn", "is_chain", "is_two_lobe"],
                       defaults=(False, False))

_R_REF = 40.0  # arbitrary reference length scale; only Rg (derived) matters for the Kratky curve
_R_BEAD = 20.0  # bead radius of the bead-assembly entries (same remark)

# Two-lobe bead models (Pedersen Eq. 59), lengths in bead radii.
# Plain dumbbell: two nearly touching spheres (centre distance 2.4 R) with a modest size spread; parameters set
# by principle, not fitted to a component.
_DUMBBELL_CENTRES = np.array([[-1.2, 0.0, 0.0], [1.2, 0.0, 0.0]])
_DUMBBELL_SPREAD = 0.12


def _tetra_dumbbell_centres(D, dd_in, twist):
    """Two bead tetrahedra (edge 2*dd_in) at x = -D and +D; the second is twisted by `twist` about the x axis."""
    t = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], float)*(dd_in*2/(2*np.sqrt(2)))
    c, s = np.cos(twist), np.sin(twist)
    rot = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return np.vstack([t + [-D, 0, 0], t @ rot.T + [D, 0, 0]])


# Dumbbell of two bead tetrahedra: parameters fitted to the two-peak Kratky curve of component 1 of Y17AH20N
# (RMSE 0.072; molass-researcher experiments 49n/49p) -- tuned to one dataset, to be validated on others.
_TETRA_DUMBBELL_CENTRES = _tetra_dumbbell_centres(2.416, 1.084, 1.07)
_TETRA_DUMBBELL_SPREAD = 0.198

# One colour per library position, shared by the shape-key icons and the overlay plots
# (the default matplotlib cycle has only 10 colours, fewer than the library's shapes).
SHAPE_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
                "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#d4a017", "#00a884"]


def get_shape_color(index):
    """Colour of the library shape at ``index`` (position in :func:`get_model_shapes`)."""
    return SHAPE_COLORS[index % len(SHAPE_COLORS)]


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


def _plot_triaxial_3d(ax, a, b, c, color):
    u = np.linspace(0, 2*np.pi, 36)
    v = np.linspace(0, np.pi, 18)
    x = a*np.outer(np.cos(u), np.sin(v))
    y = b*np.outer(np.sin(u), np.sin(v))
    z = c*np.outer(np.ones_like(u), np.cos(v))
    ax.plot_surface(x, y, z, color=color, alpha=0.9, linewidth=0)
    return max(a, b, c)


def _plot_beads_3d(ax, centres, R, color):
    u = np.linspace(0, 2*np.pi, 14)
    v = np.linspace(0, np.pi, 8)
    c0 = np.asarray(centres, float)
    c0 = c0 - c0.mean(axis=0)
    for c in c0:
        ax.plot_surface(c[0] + R*np.outer(np.cos(u), np.sin(v)), c[1] + R*np.outer(np.sin(u), np.sin(v)),
                        c[2] + R*np.outer(np.ones_like(u), np.cos(v)), color=color, alpha=0.9, linewidth=0)
    return float(np.abs(c0).max() + R)


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
        returns its bounding extent), ``.is_chain`` (True for the
        flexible-chain reference, which has no Kratky peak), and ``.is_two_lobe``
        (True for the dumbbells, whose Kratky curve has a second hump; they are
        only considered when the data show one).
    """
    cyl_R = 20.0
    ellipsoid_epss = (2.0, 3.0, 4.0, 6.0)
    # tri-axial semi-axis ratios 1 : b : c (Pedersen Eq. 62): plate-like, disc-like and ribbon-like bodies;
    # chosen as representatives of what the Y17AH20N components matched best (molass-researcher exp. 49h)
    triaxial_ratios = ((3.0, 6.0), (4.0, 5.0), (4.0, 12.0))
    rod_ratios = (10.0,)     # one long rod; shorter cylinders are matched by ellipsoids (exp. 49l/49o)

    specs = []
    specs.append(ShapeSpec("sphere", sphere_Rg(_R_REF),
                           lambda qs: sphere_F(np.asarray(qs)*_R_REF)**2,
                           lambda ax, col=SHAPE_COLORS[len(specs)]: _plot_sphere_3d(ax, _R_REF, col)))
    for eps in ellipsoid_epss:
        specs.append(ShapeSpec(f"ellipsoid (eps={eps:g})", ellipsoid_Rg(_R_REF, eps),
                               lambda qs, eps=eps: ellipsoid_P(qs, _R_REF, eps),
                               lambda ax, eps=eps, col=SHAPE_COLORS[len(specs)]: _plot_ellipsoid_3d(ax, _R_REF, eps, col)))
    for b, c in triaxial_ratios:
        a = _R_REF/2    # thinnest semi-axis; only the ratios matter
        specs.append(ShapeSpec(f"triaxial (1:{b:g}:{c:g})", triaxial_Rg(a, a*b, a*c),
                               lambda qs, a=a, b=b, c=c: triaxial_P(qs, a, a*b, a*c),
                               lambda ax, a=a, b=b, c=c, col=SHAPE_COLORS[len(specs)]: _plot_triaxial_3d(ax, a, a*b, a*c, col)))
    for ratio in rod_ratios:
        L = cyl_R*ratio
        specs.append(ShapeSpec(f"cylinder (L/R={ratio:g})", cylinder_Rg(cyl_R, L),
                               lambda qs, L=L: cylinder_P(qs, cyl_R, L),
                               lambda ax, L=L, col=SHAPE_COLORS[len(specs)]: _plot_cylinder_3d(ax, cyl_R, L, col)))
    for name, centres, spread in (("dumbbell (2 beads)", _DUMBBELL_CENTRES, _DUMBBELL_SPREAD),
                                  ("dumbbell of tetrahedra (2x4)", _TETRA_DUMBBELL_CENTRES, _TETRA_DUMBBELL_SPREAD)):
        specs.append(ShapeSpec(name, bead_assembly_Rg(centres, polydispersity=spread)*_R_BEAD,
                               lambda qs, centres=centres, spread=spread: bead_assembly_P(np.asarray(qs)*_R_BEAD, centres, polydispersity=spread),
                               lambda ax, centres=centres, col=SHAPE_COLORS[len(specs)]: _plot_beads_3d(ax, centres*_R_BEAD, _R_BEAD, col),
                               is_two_lobe=True))
    specs.append(ShapeSpec("Gaussian chain", _R_REF,
                           lambda qs: gaussian_chain_P(qs, _R_REF),
                           lambda ax, col=SHAPE_COLORS[len(specs)]: _plot_chain_3d(ax, _R_REF, col),
                           is_chain=True))
    return specs
