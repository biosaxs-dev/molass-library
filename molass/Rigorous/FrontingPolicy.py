"""
    Rigorous.FrontingPolicy
    =======================

    Fronting is allowed in the rigorous stage only for the components whose quick EGH fit shows it
    (molass-library#350).

    Fronting (a negatively skewed peak) is rare in SEC, it is visible in the elution plot, and only two
    models can represent it: EGH (``tau < 0``) and EDM (``b < 0``; with ``b > 0`` the EDM peak tails). The SDM,
    LKM and GRM models assume a linear isotherm and cannot front, so the policy does not concern them.

    The policy is one bool per elution component, ``True`` meaning "this component may front":

    - EGH rigorous: ``tau`` may be negative only for a flagged component (``tau >= 0`` otherwise);
    - EDM: ``b`` is free in its range only for a flagged component (``b >= 0`` otherwise), in the quick
      EDM stage as well as in the rigorous one.

    Ways to give it (``mode``):

    ``'auto'``    flag a component when its quick EGH fit has ``tau / sigma < FRONTING_THRESHOLD``;
    ``'allow'``   every component may front;
    ``'forbid'``  none may;
    ``'legacy'``  what molass did before #350: EGH ``tau >= 0`` (forbid), EDM ``b`` free (allow); used to
                  rebuild recipes written before the policy was recorded, so existing analysis folders resume
                  with the bounds they ran with;
    a sequence of bools   as it is.
"""
FRONTING_THRESHOLD = -0.05
"""``tau / sigma`` below this counts as fronting. Measured on the bundled samples: SAMPLE3 -0.33, every other
component |tau / sigma| < 0.01 (molass-researcher experiments 53 and 54); a single positive, so a tunable value."""

MODES = ('auto', 'allow', 'forbid', 'legacy')


def _model_of(decomposition):
    return decomposition.xr_ccurves[0].model


def _egh_source(decomposition):
    """The EGH decomposition ``decomposition`` is or was upgraded from, or ``None``."""
    seen = 0
    d = decomposition
    while d is not None and seen < 10:
        if _model_of(d) == 'egh':
            return d
        d = getattr(d, '_source_decomp', None)
        seen += 1
    return None


def detect_fronting(egh_decomposition, threshold=FRONTING_THRESHOLD):
    """One bool per component of an EGH decomposition: ``tau / sigma < threshold``."""
    flags = []
    for cc in egh_decomposition.xr_ccurves:
        _h, _m, sigma, tau = [float(v) for v in cc.get_params()[:4]]
        flags.append(bool(abs(sigma) > 0 and tau / abs(sigma) < threshold))
    return flags


def legacy_flags(model, n):
    """The policy of molass before #350 for ``model`` (EGH: no fronting, EDM: free b), ``None`` for the others."""
    if model == 'egh':
        return [False] * n
    if model == 'edm':
        return [True] * n
    return None


def resolve_fronting(decomposition, mode=None, *, target_model=None, threshold=FRONTING_THRESHOLD):
    """Resolve ``mode`` to a list of bools, one per elution component, or ``None`` if the model cannot front.

    Parameters
    ----------
    decomposition : Decomposition
        An EGH decomposition (the flags are detected from its elution curves), or the result of an
        ``upgrade()`` of one (its EGH source is used).
    mode : str, sequence of bool or None
        ``'auto'``, ``'allow'``, ``'forbid'``, ``'legacy'`` or the flags themselves (see the module
        docstring). ``None``: the flags the decomposition already carries (``fronting_flags``), else ``'auto'``.
    target_model : str, optional
        The model the flags are for, when it is not the decomposition's own, e.g. ``'edm'`` while the
        decomposition is still the EGH one ``upgrade('EDM')`` starts from.
    threshold : float, optional
        ``tau / sigma`` below which ``'auto'`` flags a component.

    Returns
    -------
    list of bool or None
        ``None`` for models that cannot front (SDM, LKM, GRM), for which the policy does not apply.
    """
    n = decomposition.num_components
    model = target_model if target_model is not None else _model_of(decomposition)
    if model not in ('egh', 'edm'):
        return None
    if mode is None:
        stored = getattr(decomposition, 'fronting_flags', None)
        if stored is not None:
            return [bool(v) for v in stored]
        mode = 'auto'
    if not isinstance(mode, str):
        flags = [bool(v) for v in mode]
        if len(flags) != n:
            raise ValueError(f"fronting has {len(flags)} entries, the decomposition has {n} components")
        return flags
    mode = mode.lower()
    if mode == 'allow':
        return [True] * n
    if mode == 'forbid':
        return [False] * n
    if mode == 'legacy':
        return legacy_flags(model, n)
    if mode != 'auto':
        raise ValueError(f"fronting must be one of {MODES}, a sequence of bools or None, not {mode!r}")
    egh = _egh_source(decomposition)
    if egh is None:
        return [True] * n           # no EGH fit to judge by: do not restrict
    return detect_fronting(egh, threshold)


def recipe_flags(decomposition):
    """The flags to record in ``recipe.json``, or ``None`` when they cannot be told (not an EGH/EDM decomposition)."""
    try:
        return resolve_fronting(decomposition, None)
    except Exception:
        return None


def describe(flags):
    """One line for summaries: which components may front."""
    if flags is None:
        return "not applicable"
    if not any(flags):
        return "none"
    if all(flags):
        return "all"
    return "component " + ", ".join(str(k + 1) for k, f in enumerate(flags) if f)
