# LKM Mass-Transfer Floor — component broadening constraint

**Status**: ✅ Implemented (2026-09-11). Tests pass; not yet exercised in a full
BH/DE run against real SAMPLE5 data (recipe_runner_notebook_redesign.ipynb
Sections 5-8 used to diagnose this only reconstruct completed jobs — this fix
needs a *new* rigorous-optimization run to confirm it changes the outcome).

## Problem

`molass-papers/experiments/recipe_runner_notebook_redesign.ipynb` (Sections
7-12) diagnosed a systematic LKM defect on the SAMPLE5 (BSA, 4-component)
dataset: components 0/1 (the two lowest-abundance species) fit unrealistically
broad, with the *specific* component that collapses differing between BH and
DE reruns of the same recipe — a sign of a genuinely unconstrained direction
in parameter space, not real chemistry.

| Analysis (method) | Component | R | k_MT | moment_std (frames) |
|---|---|---|---|---|
| analysis-007 (BH) | 0 | 1.1065 | 0.0636 | 38.72 |
| analysis-007 (BH) | 1 | 1.1065 | 2.0084 | 9.22 |
| analysis-007 (BH) | 3 (monomer) | 1.3306 | 1670.4 | 8.52 |
| analysis-008 (DE) | 0 | 1.1002 | 0.4952 | 14.53 |
| analysis-008 (DE) | 1 | 1.1994 | 0.0452 | 61.81 |
| analysis-008 (DE) | 3 (monomer) | 1.3377 | 1037.5 | 8.54 |

`k_MT` (mass-transfer rate) is the direct cause: as `k_MT -> 0`, mass-transfer
resistance dominates and the peak broadens severely; as `k_MT -> infinity`,
LKM collapses to the equilibrium-dispersive (EDM) limit and stays narrow
(exactly what the dominant, well-constrained monomer component shows). `R`
(already bounded at `R >= 1.05`) is not the problem — all fitted `R` values sit
comfortably above that bound.

## Derivation

`molass/SEC/Models/LkmLinear.py`'s transfer function:

```
H(s) = exp( Pe/2 * (1 - sqrt(1 + 4s*t0*(s+k_MT*R)/(Pe*(s+k_MT)))) )
```

Taylor-expanding `ln H(s)` to `O(s^2)` (moment-generating-function expansion:
`mu1 = -H'(0)`, `sigma^2 = H''(0) - H'(0)^2`) gives a clean two-term variance
decomposition:

```
sigma^2 = 2*t0^2*R^2/Pe        <- axial dispersion, independent of k_MT
        + 2*t0*(R-1)/k_MT      <- mass-transfer resistance
```

**Verified against the real fitted data to <1%** (predicted vs. measured
`moment_std`, all 8 components across both runs) — this is not an
approximation of unknown accuracy, it reproduces the actual LKM curve shape
almost exactly.

Requiring the total sigma to stay within a tolerance factor `m` of the
axial-only baseline (`m=1.5` chosen and sensitivity-checked, see below) gives
a per-component floor:

```
k_MT_floor(R, Pe, t0; m) = (R-1)*Pe / ((m^2-1)*t0*R^2)
```

### Sensitivity to `m`

Collapses to one number per component: `m_critical = sigma_actual / sigma_axial`
— a component fails whenever the chosen `m < m_critical`.

| Component | m_critical | Fails until m >= |
|---|---|---|
| 007/comp0 | 6.23 | never passes even at m=3.0 |
| 008/comp1 | 9.44 | never passes even at m=3.0 |
| 008/comp0 | 2.42 | 2.5 |
| 007/comp1 | 1.48 | 1.5 |
| 007/comp2 | 1.45 | 1.5 |
| 008/comp2 | 1.33 | 1.5 |
| 007/comp3, 008/comp3 (monomer) | 1.14-1.17 | always passes (>=1.2) |

The two clearly pathological components fail under any reasonable `m`; the
monomer never comes close to failing; `m=1.5` sits right at the edge of a
narrow "moderately elevated" band (1.33-1.48) rather than inside it — a
defensible default, not finely tuned.

## Implementation

- **`molass_legacy/Optimizer/PenaltyUtils.py`**: `compute_lkm_mass_transfer_penalty(Pe,
  t0, R_values, k_MT_values, tolerance=1.5, scale=3.0)`. Dimensionless
  per-component ratio penalty `scale * max(0, 1 - k_MT/k_MT_floor)^2` — using a
  ratio (not raw `k_MT - floor`) keeps the penalty comparable across datasets
  with very different `Pe`/`t0` scales. Unit-tested against the real
  analysis-007/008 values in `tests/test_lkm_mass_transfer_penalty.py`
  (11 tests, all pass) — confirms it flags exactly the 3 known-pathological
  components and passes the 5 well-behaved ones.
- **`molass_legacy/ObjectiveFunctions/G1400.py`**: computes `k_MT_values =
  lkmcol_params[4::2]` alongside the existing `R_values = lkmcol_params[3::2]`
  (R-ordering penalty), calls the new function, and appends the result to the
  `penalties` list passed to `compute_fv`.
- **`G1400.get_score_names()`** overridden (same pattern as `G0367.py`) to
  insert `"mass_transfer_penalty"` right after `"order_penalty"` in the name
  list — without this, `get_score_breakdown()`/`diagnose()` would silently
  misalign or drop this penalty from the named breakdown, since the base
  `BasicOptimizer.get_score_names()` has no slot for LKM-specific penalties.

## Not yet done / open follow-ups

- [ ] Re-run BH/DE on SAMPLE5 with this constraint active and confirm
      components 0/1 no longer collapse (the actual validation this fix needs
      — everything above is unit-level only).
- [ ] `scale=3.0` is a first guess, not calibrated against real optimizer runs
      the way `LumpingConstraint`'s `weight=0.2` was calibrated (see that
      module's docstring: "a full 25-frame crossing costs ~5 fv units"). Worth
      similar calibration once a real run is available.
- [ ] Consider whether SDM/EDM/GRM have an analogous unconstrained-broadening
      failure mode for low-abundance components, or whether this is
      LKM-specific (plausible, since SDM/EDM don't have a `k_MT`-like free
      parameter that can independently collapse per component).
- [ ] GitHub issue not yet opened (AI Improvement Feedback Loop, Rule 11) —
      do so if/when the real-run validation above confirms this works.

## Source

`molass-papers/experiments/recipe_runner_notebook_redesign.ipynb`, Sections
7-12 (component broadness diagnosis, actual LKM parameter values, floor
derivation, sensitivity analysis).
