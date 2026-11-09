"""
Kratky.FormFactors

Exact analytical form factors (and their exact Rg relations) from
J.S. Pedersen (1997), "Analysis of small-angle scattering data from colloids
and polymer solutions: modeling and least-squares fitting", Adv. Colloid
Interface Sci. 70:171-210. Equation numbers below refer to that paper.

Signatures (``qs`` in inverse length; each ``*_Rg`` returns a length in the
unit of the shape parameters, so ``qs * Rg`` is dimensionless):

=====================  ===========================  ===========================
form factor            parameters                   Rg
=====================  ===========================  ===========================
``sphere_P``           ``(qs, R)``                  ``sphere_Rg(R)``
``ellipsoid_P``        ``(qs, R, eps)``             ``ellipsoid_Rg(R, eps)``
``triaxial_P``         ``(qs, a, b, c)``            ``triaxial_Rg(a, b, c)``
``cylinder_P``         ``(qs, R, L)``               ``cylinder_Rg(R, L)``
``gaussian_chain_P``   ``(qs, Rg)``                 (is its argument)
``sphere_chains_P``    ``(qs, R, rg_c, phi,         ``sphere_chains_Rg(R, rg_c, phi,
                       n_chains=1,                  n_chains=1, nonpenetrating=True)``
                       nonpenetrating=True)``
``fold_unfold_P``      ``(qs, rg_fold, rg_unfold,   ``fold_unfold_Rg(rg_fold, rg_unfold,
                       f_unfold)``                  f_unfold)``
``bead_assembly_P``    ``(qs, centres, radii=None,  ``bead_assembly_Rg(centres,
                       polydispersity=0.0)``        radii=None, polydispersity=0.0)``
=====================  ===========================  ===========================

``bead_assembly_*`` take centres and radii in one common length unit (the
default radius is 1, so centres are then in bead radii).

Physics only -- no application logic (peak-finding, classification, plotting)
lives here. See ``molass.Kratky.ShapeMatch`` for that.
"""
import numpy as np
from scipy.special import j1
from scipy.integrate import quad


def sphere_F(x):
    """Pedersen Eq. 55: homogeneous sphere scattering amplitude. x = q*R."""
    x = np.asarray(x, dtype=float)
    out = np.ones_like(x)
    nz = x != 0
    xn = x[nz]
    out[nz] = 3*(np.sin(xn) - xn*np.cos(xn)) / xn**3
    return out


def sphere_P(qs, R):
    """Homogeneous sphere form factor P(q) = F(q)^2."""
    return sphere_F(np.asarray(qs)*R)**2


def sphere_Rg(R):
    """Exact sphere Rg: Rg^2 = (3/5) R^2 (Kratky 1963, Eq. 4)."""
    return R*np.sqrt(3/5)


def ellipsoid_P_single(q, R, eps):
    """Pedersen Eq. 61: ellipsoid of revolution, semi-axes (R, R, eps*R),
    orientation-averaged over alpha in [0, pi/2]."""
    def integrand(alpha):
        r = R*np.sqrt(np.sin(alpha)**2 + eps**2*np.cos(alpha)**2)
        return sphere_F(np.array([q*r]))[0]**2 * np.sin(alpha)
    val, _ = quad(integrand, 0, np.pi/2)
    return val


def ellipsoid_P(qs, R, eps):
    """Ellipsoid of revolution form factor, vectorized over qs."""
    return np.array([ellipsoid_P_single(q, R, eps) for q in np.atleast_1d(qs)])


def ellipsoid_Rg(R, eps):
    """Exact ellipsoid-of-revolution Rg: Rg^2 = R^2 (2 + eps^2) / 5."""
    return R*np.sqrt((2 + eps**2)/5)


_TRI_U, _TRI_W = np.polynomial.legendre.leggauss(48)
_TRI_U = 0.5*(_TRI_U + 1)           # u = cos(alpha) in [0, 1]
_TRI_W = 0.5*_TRI_W
_TRI_PHI = 0.5*np.pi*_TRI_U         # phi in [0, pi/2]; the mean over phi is sum(W * f)


def triaxial_P(qs, a, b, c):
    """Pedersen Eq. 62: tri-axial ellipsoid with semi-axes a, b, c, orientation-averaged
    (Gauss-Legendre in cos(alpha) and in phi; vectorized over qs)."""
    qs = np.atleast_1d(np.asarray(qs, float))
    r = np.sqrt((a**2*np.sin(_TRI_PHI)**2 + b**2*np.cos(_TRI_PHI)**2)[:, None]*(1 - _TRI_U**2)[None, :]
                + c**2*(_TRI_U**2)[None, :])                       # (n_phi, n_u)
    out = np.empty_like(qs)
    for k, q in enumerate(qs):
        out[k] = np.einsum("i,j,ij->", _TRI_W, _TRI_W, sphere_F(q*r)**2)
    return out


def triaxial_Rg(a, b, c):
    """Exact tri-axial ellipsoid Rg: Rg^2 = (a^2 + b^2 + c^2) / 5."""
    return np.sqrt((a**2 + b**2 + c**2)/5)


_GH_NODES, _GH_WEIGHTS = np.polynomial.hermite_e.hermegauss(13)
_GH_WEIGHTS = _GH_WEIGHTS/_GH_WEIGHTS.sum()


def _sphere_amplitude(x):
    """Sphere amplitude F(x) with a series for small x (avoids cancellation)."""
    x = np.asarray(x, float)
    out = np.empty_like(x)
    small = np.abs(x) < 1e-2
    xs = x[small]
    out[small] = 1 - xs**2/10 + xs**4/280
    xb = x[~small]
    out[~small] = 3*(np.sin(xb) - xb*np.cos(xb))/xb**3
    return out


def bead_assembly_P(qs, centres, radii=None, polydispersity=0.0):
    """Pedersen Eq. 59 (Debye 1915): particle made of homogeneous spherical subunits, orientation-averaged.

    P(q) = sum_ij V_i V_j F(q r_i) F(q r_j) sin(q d_ij)/(q d_ij) / (sum V)^2, P(0) = 1.

    Parameters
    ----------
    qs : array_like
    centres : array_like, shape (n, 3)
        Centres of the beads (same length unit as ``radii`` and ``1/qs``).
    radii : array_like, optional
        Bead radii (default: all 1).
    polydispersity : float, optional
        Relative size spread (log-normal sigma) of the *whole* object. The curve is averaged over scaled copies,
        which smears the deep minima of the sphere form factor -- a stand-in for irregular, non-spherical subunits
        (see molass-researcher experiments 49d/49n). The exact Rg of the smeared form factor is given by
        :func:`bead_assembly_Rg` with the same polydispersity.
    """
    qs = np.atleast_1d(np.asarray(qs, float))
    c = np.asarray(centres, float)
    r = np.ones(len(c)) if radii is None else np.asarray(radii, float)
    V = r**3
    d = np.linalg.norm(c[:, None] - c[None, :], axis=-1)

    def once(q):
        A = _sphere_amplitude(q[:, None]*r[None, :])*V[None, :]
        z = q[:, None, None]*d[None]
        S = np.where(z > 1e-8, np.sin(z)/np.where(z > 1e-8, z, 1.0), 1.0)
        return np.einsum("qi,qj,qij->q", A, A, S)/V.sum()**2

    if polydispersity < 1e-3:
        return once(qs)
    return sum(w*once(qs*np.exp(polydispersity*g - 0.5*polydispersity**2)) for g, w in zip(_GH_NODES, _GH_WEIGHTS))


def bead_assembly_Rg(centres, radii=None, polydispersity=0.0):
    """Exact Rg of :func:`bead_assembly_P`: Rg^2 = sum V_i (3/5 r_i^2 + |c_i - c_cm|^2) / sum V,
    times exp(sigma^2/2) for a log-normal size spread sigma (the smeared form factor's Guinier radius)."""
    c = np.asarray(centres, float)
    r = np.ones(len(c)) if radii is None else np.asarray(radii, float)
    V = r**3
    cm = (V[:, None]*c).sum(0)/V.sum()
    rg0 = np.sqrt((V*(0.6*r**2 + ((c - cm)**2).sum(1))).sum()/V.sum())
    return float(rg0*np.exp(0.5*polydispersity**2))


def cylinder_P_single(q, R, L):
    """Pedersen Eq. 64: cylinder, radius R, length L. B1 = first-order Bessel J1."""
    def integrand(alpha):
        x = q*R*np.sin(alpha)
        cross = 1.0 if x == 0 else 2*j1(x)/x
        y = q*L*np.cos(alpha)/2
        length = 1.0 if y == 0 else np.sin(y)/y
        return (cross*length)**2 * np.sin(alpha)
    val, _ = quad(integrand, 0, np.pi/2, limit=200)
    return val


def cylinder_P(qs, R, L):
    """Cylinder form factor, vectorized over qs."""
    return np.array([cylinder_P_single(q, R, L) for q in np.atleast_1d(qs)])


def cylinder_Rg(R, L):
    """Exact cylinder Rg: Rg^2 = R^2/2 + L^2/12 (Kratky 1963, Eq. 4)."""
    return np.sqrt(R**2/2 + L**2/12)


def gaussian_chain_P(qs, Rg):
    """Pedersen Eq. 70 (Debye function): flexible, non-self-avoiding
    (ideal random-walk) polymer chain. u = (q*Rg)^2."""
    qs = np.atleast_1d(qs)
    u = (qs*Rg)**2
    out = np.ones_like(u, dtype=float)
    nz = u > 1e-8
    un = u[nz]
    out[nz] = 2*(np.exp(-un) + un - 1)/un**2
    return out


def sphere_chains_P(qs, R, rg_c, phi, n_chains=1, nonpenetrating=True):
    """Pedersen item 25 (Pedersen and Gerstenberg 1996): a sphere of radius ``R`` with ``n_chains`` Gaussian
    chains attached, each of radius of gyration ``rg_c``; a folded core with disordered tails.

    ``phi`` is the share of the total scattering mass carried by the chains (all chains together), so the
    sphere carries ``1 - phi``; ``P(0) = 1``. ``nonpenetrating`` replaces ``R`` by ``R + rg_c`` in the
    sin(x)/x terms of the sphere-chain and chain-chain cross terms, as Pedersen recommends for ``R >> rg_c``.
    """
    qs = np.asarray(qs, dtype=float)
    rs, rc = 1.0 - phi, phi/n_chains
    Fs = sphere_F(qs*R)
    u = (qs*rg_c)**2
    psi = np.where(u > 1e-8, (1.0 - np.exp(-u))/np.where(u > 1e-8, u, 1.0), 1.0)
    x = qs*(R + rg_c if nonpenetrating else R)
    sinc = np.where(x > 1e-8, np.sin(x)/np.where(x > 1e-8, x, 1.0), 1.0)
    cross = psi*sinc
    return (rs**2*Fs**2 + n_chains*rc**2*gaussian_chain_P(qs, rg_c) + n_chains*(n_chains - 1)*rc**2*cross**2
            + 2*n_chains*rs*rc*Fs*cross)


def sphere_chains_Rg(R, rg_c, phi, n_chains=1, nonpenetrating=True):
    """Radius of gyration of :func:`sphere_chains_P`, from the small-q expansion ``P = 1 - q^2 G / 3``:
    ``G = rs^2 Rs^2 + Nc rc^2 Rc^2 + Nc (Nc - 1) rc^2 (3 Rc^2 + d^2) + Nc rs rc (Rs^2 + 3 Rc^2 + d^2)`` with the
    mass shares ``rs``, ``rc`` of the sphere and of one chain, ``Rs^2 = 3 R^2 / 5`` and ``d`` the distance of the
    chain start from the centre (``R``, or ``R + rg_c`` when non-penetrating)."""
    rs, rc = 1.0 - phi, phi/n_chains
    Rs2, Rc2 = 0.6*R**2, rg_c**2
    d2 = (R + rg_c)**2 if nonpenetrating else R**2
    G = (rs**2*Rs2 + n_chains*rc**2*Rc2 + n_chains*(n_chains - 1)*rc**2*(3*Rc2 + d2)
         + n_chains*rs*rc*(Rs2 + 3*Rc2 + d2))
    return np.sqrt(G)


def fold_unfold_P(qs, rg_fold, rg_unfold, f_unfold):
    """Fast-exchange population mix of a folded state (homogeneous sphere of radius of gyration ``rg_fold``) and
    an unfolded state (Gaussian chain of radius of gyration ``rg_unfold``) of equal mass; ``f_unfold`` is the
    unfolded fraction. ``P(0) = 1``."""
    qs = np.asarray(qs, dtype=float)
    return (1 - f_unfold)*sphere_P(qs, rg_fold/np.sqrt(0.6)) + f_unfold*gaussian_chain_P(qs, rg_unfold)


def fold_unfold_Rg(rg_fold, rg_unfold, f_unfold):
    """Radius of gyration of :func:`fold_unfold_P`: ``Rg^2 = (1 - f) Rg_fold^2 + f Rg_unfold^2``."""
    return np.sqrt((1 - f_unfold)*rg_fold**2 + f_unfold*rg_unfold**2)
