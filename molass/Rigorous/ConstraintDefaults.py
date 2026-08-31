"""Rigorous.ConstraintDefaults

Single source of truth for the auto-applied DE/LumpingConstraint condition and
its accompanying solver-setting overrides (issue #255).  Before this module
existed, RigorousImplement.py (parent process) and RecipeRunner.py
(subprocess) each independently re-derived
``method == 'DE' and n_components >= 3 -> auto-apply LumpingConstraint``.
#253's bug was exactly a safety override (``de_tol=0``) added alongside this
condition in the parent's copy but not mirrored into the subprocess's copy.
Both callers now go through :func:`get_constraint_and_overrides` instead.
"""


def get_constraint_and_overrides(method, n_components, decomp):
    """Return the constraints and solver-setting overrides auto-applied for
    this ``(method, n_components)`` combination.

    Parameters
    ----------
    method : str
        Optimization method, case-insensitive (e.g. ``'DE'``, ``'de'``).
    n_components : int
        Number of components in the decomposition.
    decomp : Decomposition
        Source decomposition used to build the constraint's zone boundaries.
        Callers should pass the pre-upgrade EGH source when available (EGH
        curves give more reliable peak positions than physics-model curves)
        -- see the ``_source_decomp``/``_parent`` fallback chain used by both
        callers.

    Returns
    -------
    constraints : list or None
        ``[LumpingConstraint(decomp)]`` when auto-applied, else ``None``.
    settings_overrides : dict
        SerialSettings overrides to apply alongside the constraints (e.g.
        ``{'de_tol': 0}``); empty when nothing was auto-applied.
    """
    if method.upper() == 'DE' and n_components >= 3:
        from molass.Rigorous.LumpingConstraint import LumpingConstraint
        constraint = LumpingConstraint(decomp)
        # Penalty terms reshape the fitness landscape so scipy DE's
        # std(energies) <= tol*mean early-convergence check fires too soon.
        return [constraint], {'de_tol': 0}
    return None, {}
