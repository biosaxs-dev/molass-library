"""Rigorous.ConstraintDefaults

Single source of truth for the auto-applied LumpingConstraint condition and
its accompanying solver-setting overrides (issue #255).  Before this module
existed, RigorousImplement.py (parent process) and RecipeRunner.py
(subprocess) each independently re-derived
``method == 'DE' and n_components >= 3 -> auto-apply LumpingConstraint``.
#253's bug was exactly a safety override (``de_tol=0``) added alongside this
condition in the parent's copy but not mirrored into the subprocess's copy.
Both callers now go through :func:`get_constraint_and_overrides` instead.

The constraint itself applies uniformly to any method (BH or DE) and any
model (EGH/SDM/EDM/CEDM/LKM/GRM) with 3+ components -- component collapse is
not a DE-specific failure mode, and the boundaries are always derived from
the pre-upgrade EGH source, independent of the later model choice. Only the
accompanying ``de_tol=0`` override is DE-specific (works around a scipy DE
convergence-check quirk that doesn't apply to BH).
"""


def get_constraint_and_overrides(method, n_components, decomp, weight=None):
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
    weight : float, optional
        Per-frame penetration penalty passed to ``LumpingConstraint``. When
        ``None`` (default), uses ``LumpingConstraint``'s own default (0.2),
        calibrated for confident, independently-detected peak positions. Pass
        a smaller value (e.g. 0.01) when the reference positions come from a
        low-confidence fallback (e.g. an equal-area-split decomposition) --
        still blocks gross collapse/drift, without over-penalizing legitimate
        refinement near an unconfirmed default (molass-gui#AI-friendliness).

    Returns
    -------
    constraints : list or None
        ``[LumpingConstraint(decomp, weight=weight)]`` when auto-applied, else ``None``.
    settings_overrides : dict
        SerialSettings overrides to apply alongside the constraints (e.g.
        ``{'de_tol': 0}``); empty when nothing was auto-applied.
    """
    if n_components >= 3:
        from molass.Rigorous.LumpingConstraint import LumpingConstraint
        constraint = LumpingConstraint(decomp) if weight is None else LumpingConstraint(decomp, weight=weight)
        if method.upper() == 'DE':
            # Penalty terms reshape the fitness landscape so scipy DE's
            # std(energies) <= tol*mean early-convergence check fires too soon.
            return [constraint], {'de_tol': 0}
        return [constraint], {}
    return None, {}
