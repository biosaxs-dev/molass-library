"""
    SEC.Models.EdmFunction.py

    The one documented public function of the nonlinear equilibrium dispersive model (EDM):
    :func:`edm_curve` (molass-library#356).
"""
import numpy as np


def edm_curve(x, *, t0=0.0, u, a, b, e, Dz, c_inj):
    """Elution curve of the equilibrium dispersive model (EDM) with a quadratic isotherm.

    Outlet concentration of a column of length ``L = 30`` (fixed, in column lengths) after an
    injection of duration ``t_inj = 1``, from the Hopf-Cole analytic solution of Rehman (2022).
    This is the curve molass uses for the ``'EDM'`` elution model. Underneath there are two older entry
    points: ``molass_legacy.SecTheory.Edm.edm_func(t, u, a, b, e, Dz, c_inj)`` (no shift) and
    ``molass_legacy.Models.RateTheory.EDM.edm_impl(x, t0, u, a, b, e, Dz, c_inj)`` (with the shift; the order
    of the parameter vector of an ``EdmComponentCurve``). Both give exactly the values of this function; the
    ``Edm`` class of molass-legacy takes its arguments in yet another order and fails for ``b = 0``.

    Parameters
    ----------
    x : array-like
        Time (frame) values.
    t0 : float, optional
        Time shift: the curve is ``edm_func(x - t0, ...)``. Default 0.
    u : float
        Mobile-phase velocity in column lengths per time unit.
    a : float
        Henry coefficient (initial slope of the isotherm) = ``K_SEC`` x ``Vp/V0``, with ``K_SEC`` the
        partition coefficient of SEC and ``Vp/V0`` the pore-to-void volume ratio.
    b : float
        Curvature (nonlinearity) of the isotherm; **the sign decides the peak asymmetry**:

        * ``b > 0``: a tailing peak (positive skewness; Langmuir-type isotherm),
        * ``b = 0``: the linear isotherm, a nearly symmetric peak (positive skewness of about 0.2
          from the axial dispersion alone, for typical values),
        * ``b < 0``: a fronting peak (negative skewness; anti-Langmuir-type isotherm).

        In SEC, tailing is normally kinetic (``b`` about 0), not adsorptive, and fronting is rare.
    e : float
        Mobile-phase fraction of the *accessible* volume, ``e = V0 / (V0 + Vp)`` (phase ratio
        ``F = (1 - e) / e = Vp / V0``). Not the total porosity of the column.
    Dz : float
        Axial dispersion coefficient (Peclet number ``Pe = L u / Dz``).
    c_inj : float
        Injected concentration.

    Returns
    -------
    numpy.ndarray
        The curve at ``x``; ``0`` where the injection has not yet reached the outlet.

    Notes
    -----
    **The limit b -> 0.** The solution has a removable singularity at ``b = 0``; for ``|b| < 1e-9`` the
    linear-isotherm limit (a Gaussian-like advection-dispersion peak) is evaluated directly, so the curve
    is continuous in ``b`` (at ``b = 1e-3`` it differs from the ``b = 0`` curve by less than 0.1 % of the
    height, for typical values).

    **Linearization of the isotherm.** The isotherm is expanded around the reference concentration
    ``c0 = 1e-4`` (the ``c0`` of ``edm_func``, not a parameter here): the retention factor uses
    ``gam2 = (a + 3 a b c0) / (1 + b c0)**3``, about ``a``, and the curvature
    ``gam3 = -a b / (1 + b c0)**3``, about ``-a b``. Only the Henry coefficient ``a`` and the local
    curvature ``-a b`` enter.

    **What the shape depends on.** The strength of the nonlinearity is ``Beta = lam Pe c_inj t_inj u / (2 L)``
    with ``lam = 2 F gam3 / R`` and ``R = 1 + gam2 F``, i.e. proportional to ``-F a b c_inj / R``: for fixed
    ``a, e, u, Dz`` the *normalized* peak shape depends on ``b`` and ``c_inj`` only through the product
    ``b * c_inj`` (the curves agree to within about 0.2 % of the peak height for typical values; the small
    rest comes from the reference concentration ``c0``), while the height scales as ``1 / b`` at fixed
    ``b * c_inj``. ``a`` is not interchangeable with ``b``: it also sets the retention (``R``), so fixing the
    product ``a * b`` does not fix the shape.

    References
    ----------
    Rehman, J. U. (2022), Analysis of equilibrium dispersive model of liquid chromatography considering a
    quadratic-type adsorption isotherm (Hopf-Cole solution).

    Examples
    --------
    >>> import numpy as np
    >>> from molass.SEC.Models.EdmFunction import edm_curve
    >>> t = np.linspace(0.01, 400, 4000)
    >>> tailing = edm_curve(t, u=0.5, a=1.0, b=1.0, e=0.4, Dz=0.05, c_inj=1.5)     # b > 0
    >>> fronting = edm_curve(t, u=0.5, a=1.0, b=-1.0, e=0.4, Dz=0.05, c_inj=1.5)   # b < 0
    """
    from molass_legacy.SecTheory.Edm import edm_func
    x = np.asarray(x, dtype=float)
    return edm_func(x - t0, u, a, b, e, Dz, c_inj)
