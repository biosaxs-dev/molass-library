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
