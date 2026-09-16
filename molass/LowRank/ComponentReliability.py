"""
LowRank.ComponentReliability.py

Per-component reliability scoring for Decomposition objects.

The score combines two signals:
  - **Rg distinctiveness** (70 %): how well separated this component's Rg is
    from the nearest other component's Rg (relative separation).  A score of 0
    means two components have the same Rg (physically implausible); 1 means they
    are well-separated (≥ 30 % relative difference).
  - **Proportion** (30 %): components with a very small area fraction (< 5 %)
    are likely noise artifacts.

Special cases:
  - If Guinier fitting failed (Rg is ``nan``), or the Rg came from
    ``RgEstimator``'s last-resort fallback in its *saturated* (clipped, no
    real magnitude information) state: score = 0.0. Note that a saturated
    fallback Rg is a finite number, not ``nan`` -- this case is only caught by
    checking ``RgEstimator.saturated`` (see molass-library issue #273).
  - Otherwise, a non-``'legacy'``/``'legacy_relaxed'`` ``rg_source`` (i.e. the
    Rg was recovered via DENSS or a non-saturated heuristic fallback rather
    than a fully qRg-validated fit) discounts the score by a fixed confidence
    factor -- see ``_RG_SOURCE_CONFIDENCE``.
  - If there is only one component: Rg distinctiveness is inapplicable; score
    is determined by proportion alone.

The threshold for ``is_component_reliable`` defaults to 0.5.
"""
import math


# Relative Rg separation mapped to rg_score = 1 (clearly distinct)
_RG_SEP_FULL = 0.3

# Proportion mapped to prop_score = 1 (clearly non-trivial)
_PROP_FULL = 0.05

_W_RG = 0.7
_W_PROP = 0.3

# Confidence discount applied per RgEstimator.rg_source (see molass-library
# #273): a fully qRg-validated legacy fit is trusted at face value; a Rg
# recovered via DENSS (no qRg check at all) or the heuristic fallback (in its
# non-saturated state) is real but less certain, so component reliability is
# discounted accordingly. Unknown/missing rg_source defaults to full trust.
_RG_SOURCE_CONFIDENCE = {
    'legacy': 1.0,
    'legacy_relaxed': 1.0,
    'denss': 0.8,
    'fallback': 0.6,
}


def _rg_score(rg_i, other_valid_rgs):
    """Rg distinctiveness score in [0, 1] for component i."""
    if not other_valid_rgs:
        return 1.0   # only valid component — nothing to compare against
    nearest_sep = min(
        abs(rg_i - rg_j) / ((rg_i + rg_j) / 2.0)
        for rg_j in other_valid_rgs
    )
    return min(1.0, nearest_sep / _RG_SEP_FULL)


def _confidence_and_saturation(decomp, n):
    """Best-effort per-component (confidence_factor, saturated) pairs derived
    from each component's RgEstimator (``rg_source``/``saturated`` -- see
    molass-library #273). Falls back to full confidence / not-saturated for
    any component (or entirely) if guinier objects are unavailable, so callers
    without a real ``Decomposition`` (e.g. tests using a stub) are unaffected.
    """
    try:
        guinier_objects = decomp.get_guinier_objects()
        if len(guinier_objects) != n:
            raise ValueError("guinier_objects length mismatch")
    except Exception:
        return [1.0] * n, [False] * n
    confidences = [_RG_SOURCE_CONFIDENCE.get(getattr(sg, 'rg_source', 'legacy'), 1.0)
                   for sg in guinier_objects]
    saturations = [bool(getattr(sg, 'saturated', False)) for sg in guinier_objects]
    return confidences, saturations


def component_quality_scores(decomp):
    """
    Compute a per-component reliability score in [0, 1].

    Parameters
    ----------
    decomp : Decomposition
        A decomposition object returned by ``quick_decomposition()``.

    Returns
    -------
    scores : list of float
        Reliability score for each component.  Higher is more reliable.

        - 1.0 → strongly reliable (distinct Rg, non-trivial proportion)
        - 0.0 → Guinier fitting failed, or Rg is identical to another component

    Notes
    -----
    The score blends two signals:

    * **Rg distinctiveness** (weight 0.7): relative Rg separation from the
      nearest other component, normalised so that 30 % relative separation
      gives a score of 1.
    * **Proportion** (weight 0.3): area fraction normalised so that 5 %
      proportion gives a score of 1.

    When there is only one component, Rg distinctiveness is inapplicable and
    the score is derived from proportion alone.
    """
    rgs = decomp.get_rgs()
    proportions = decomp.get_proportions()
    n = len(rgs)
    confidences, saturations = _confidence_and_saturation(decomp, n)

    scores = []
    for i in range(n):
        rg_i = rgs[i]
        prop_i = float(proportions[i])

        # Hard gate: Guinier failed outright, or the Rg is a saturation
        # artifact from RgEstimator's last-resort fallback (a clipped value
        # carrying no real magnitude information at all).
        if math.isnan(rg_i) or saturations[i]:
            scores.append(0.0)
            continue

        prop_s = min(1.0, prop_i / _PROP_FULL)

        if n == 1:
            # Cannot assess Rg uniqueness with a single component
            scores.append(round(prop_s * confidences[i], 4))
            continue

        other_valid = [rgs[j] for j in range(n) if j != i and not math.isnan(rgs[j]) and not saturations[j]]
        rg_s = _rg_score(rg_i, other_valid)

        score = (_W_RG * rg_s + _W_PROP * prop_s) * confidences[i]
        scores.append(round(score, 4))

    return scores


def is_component_reliable(decomp, index, threshold=0.5):
    """
    Return ``True`` if component *index* has a quality score above *threshold*.

    Parameters
    ----------
    decomp : Decomposition
        A decomposition object.
    index : int
        Zero-based component index.
    threshold : float, optional
        Minimum score to be considered reliable.  Default 0.5.

    Returns
    -------
    bool
    """
    scores = component_quality_scores(decomp)
    return scores[index] >= threshold
