"""
Kratky.FormFactors

Exact analytical form factors (and their exact Rg relations) from
J.S. Pedersen (1997), "Analysis of small-angle scattering data from colloids
and polymer solutions: modeling and least-squares fitting", Adv. Colloid
Interface Sci. 70:171-210. Equation numbers below refer to that paper.

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
