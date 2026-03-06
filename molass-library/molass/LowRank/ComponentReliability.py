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
  - If Guinier fitting failed (Rg is ``nan``): score = 0.0.
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


def _rg_score(rg_i, other_valid_rgs):
    """Rg distinctiveness score in [0, 1] for component i."""
    if not other_valid_rgs:
        return 1.0   # only valid component — nothing to compare against
    nearest_sep = min(
        abs(rg_i - rg_j) / ((rg_i + rg_j) / 2.0)
        for rg_j in other_valid_rgs
    )
    return min(1.0, nearest_sep / _RG_SEP_FULL)


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

    scores = []
    for i in range(n):
        rg_i = rgs[i]
        prop_i = float(proportions[i])

        # Hard gate: Guinier failed
        if math.isnan(rg_i):
            scores.append(0.0)
            continue

        prop_s = min(1.0, prop_i / _PROP_FULL)

        if n == 1:
            # Cannot assess Rg uniqueness with a single component
            scores.append(round(prop_s, 4))
            continue

        other_valid = [rgs[j] for j in range(n) if j != i and not math.isnan(rgs[j])]
        rg_s = _rg_score(rg_i, other_valid)

        score = _W_RG * rg_s + _W_PROP * prop_s
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
