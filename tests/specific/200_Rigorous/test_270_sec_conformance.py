"""
Tests for the model-agnostic SEC_conformance formula (issue #289).

conformance_score() is a pure function of per-component (tR, sigma) moments -- no
optimizer, no disk I/O, no dataset needed. See molass-researcher experiment 46
(experiments/46_sec_conformance_fairness) for the design derivation and the
empirical measurement of the cross-model bias this replaces.
"""
import numpy as np
import pytest
from molass.SEC.Models.MartinSynge import (
    conformance_score,
    NEUTRAL_RAW_CONFORMANCE,
    SECCONF_LOWER_BOUND,
)


def test_single_component_returns_neutral_constant():
    """nc=1: no regression is possible with a single point -- neutral, not best."""
    assert conformance_score([100.0], [10.0]) == NEUTRAL_RAW_CONFORMANCE


def test_single_component_is_neutral_regardless_of_values():
    """The nc=1 constant must not depend on the actual tR/sigma values (no model
    should be able to game it by construction)."""
    assert conformance_score([5.0], [1.0]) == conformance_score([5000.0], [900.0])


@pytest.mark.parametrize("nc", [2, 3, 5])
def test_perfectly_consistent_moments_hit_the_floor(nc):
    """Component moments that exactly satisfy tR_i = tI + sqrt(N)*sigma_i (for a
    physically valid tI, N) should score at the best-possible floor."""
    tI, N = 10.0, 900.0
    sigma = np.linspace(5.0, 20.0, nc)
    tR = tI + np.sqrt(N) * sigma
    assert conformance_score(tR, sigma) == SECCONF_LOWER_BOUND


def test_inconsistent_moments_score_worse_than_consistent():
    """Reversing the tR/sigma order (wider peak eluting earlier) violates the
    theory and must score worse (higher/less-negative) than a consistent fit."""
    consistent = conformance_score([80.0, 100.0, 120.0], [8.0, 10.0, 12.0])
    inconsistent = conformance_score([80.0, 100.0, 120.0], [12.0, 8.0, 10.0])
    assert inconsistent > consistent


def test_small_perturbation_scores_between_perfect_and_grossly_wrong():
    """A small, physically-plausible deviation should score strictly between the
    perfect-fit floor and a grossly inconsistent case -- i.e. the formula is a
    genuine, continuously-varying residual, not another constant/shortcut."""
    tI, N = 10.0, 900.0
    sigma = np.array([8.0, 10.0, 12.0])
    tR_perfect = tI + np.sqrt(N) * sigma
    tR_noisy = tR_perfect + np.array([0.5, -0.3, 0.2])

    perfect = conformance_score(tR_perfect, sigma)
    noisy = conformance_score(tR_noisy, sigma)
    grossly_wrong = conformance_score([80.0, 100.0, 120.0], [12.0, 8.0, 10.0])

    assert perfect == SECCONF_LOWER_BOUND
    assert perfect < noisy < grossly_wrong


def test_never_exceeds_lower_bound():
    """The floor must never be breached even for extremely consistent data
    (log10 of a near-zero residual could otherwise go to -inf)."""
    tI, N = 0.0, 10000.0
    sigma = np.array([1.0, 2.0, 3.0])
    tR = tI + np.sqrt(N) * sigma
    assert conformance_score(tR, sigma) >= SECCONF_LOWER_BOUND
