# Bounded LRF Implementation Plan

## Goal

Replace the current naïve rank-2 factorization (`P = M_ @ pinv(C)`) with
Bounded LRF — a physics-constrained version that clips B(q) within the
envelope `|B(q)| ≤ A(q) / (c₁ · (qLR)²)` and redistributes excess to A(q).

Only Bounded LRF will be implemented. Synthesized LRF (logistic splice of two
decompositions) is not needed — see `explorations/bounded_structure_factorization.ipynb`.

---

## Current Architecture

### Data flow (rank-2 case)

```
Decomposition.get_xr_matrices()
  → compute_lowrank_matrices(xr.M, xr_ccurves, xr.E, xr_ranks)
      → M_ = get_denoised_data(M, svd_rank)
      → C  = [c, c²]                    # concentration matrix
      → P  = M_ @ pinv(C)               # naïve factorization → [A(q), B(q)]
      → Pe = compute_propagated_error()
      → return (M_, C_, P_, Pe)
```

### What Decomposition currently stores

```python
# Set during __init__
self.ssd              # SecSaxsData → has self.xr.qv, self.xr.M, self.xr.E
self.xr               # XrData (shortcut)
self.xr_icurve        # elution i-curve
self.xr_ccurves       # list of ComponentCurve (one per peak)
self.xr_ranks         # None → [1,1,...]; or [1,2,...] if SCD detected

# Lazily computed
self.guinier_objects   # list of RgEstimator (from XrComponent)
```

### How rank=2 is triggered

```
decomposition.compute_scds()       → [scd_1, scd_2, ...]
RankEstimator.scd_to_rank(scd)     → 2 if scd ≥ 5.0
decomposition.update_xr_ranks([1, 2, ...])
decomposition.get_xr_matrices()    → rank-2 factorization for that component
```

---

## New Variables Required by Bounded LRF

The `coerce_bounds` algorithm needs the following inputs:

| Variable | Type | Source | Description |
|----------|------|--------|-------------|
| `qv` | ndarray | `self.xr.qv` | q-vector (already available) |
| `Rg` | float | Guinier of initial P[:,0] | Radius of gyration (per component) |
| `R` | float | `√(5/3) · Rg` | Sphere-equivalent radius |
| `K` | float | fitted | Structure factor amplitude |
| `L` | float | fitted | Bound-tightness parameter |
| `c1` | float | `C[0, j_peak]` | Monomer concentration at peak |
| `c2` | float | `C[1, j_peak]` or `c1²` | Squared concentration at peak |

And it produces:

| Output | Type | Description |
|--------|------|-------------|
| `P_corrected` | ndarray | Corrected [A(q), B(q)] matrix |
| `bq_bounds` | tuple of ndarray | (−bound, +bound) envelope |
| `coerced_bq` | ndarray | Clipped B(q) |
| `K, L` | float | Fitted parameters (diagnostic) |

---

## Design Question: Where Do These Fit?

Three options were considered. **Option B** was chosen, with the refinement that
the bounding orchestration lives in `Decomposition.get_xr_matrices()` (not inside
`compute_lowrank_matrices`), and `guinier_objects` are pre-populated from naïve P.

See Section 2 below for the definitive `get_xr_matrices()` pseudo-code.

### Decision: Option B with shared Rg

Start with a single `self.bounded_lrf_info` dict keyed by component index.
This keeps the initial implementation light while preserving all diagnostic data.

Additionally, the Rg computed from the naïve P is **shared** — used both for
bounding and cached as `self.guinier_objects` — avoiding redundant computation.

---

## Concerned Interaction Points

### 1. `qv` propagation

Currently `compute_lowrank_matrices` does not receive `qv`. It needs it to:
- Compute the bound envelope `1/(qv·L·R)²`

**`qv` is available** at the call site:
- `Decomposition.get_xr_matrices()` accesses `self.xr.qv`

However, we choose **not** to pass `qv` into `compute_lowrank_matrices`.
Instead, the bounding step is orchestrated in `Decomposition.get_xr_matrices()`,
keeping `compute_lowrank_matrices` a pure factorization function.

Note: `get_uv_matrices()` uses wavelength `wv`, not `qv`. Bounded LRF applies only to XR.

### 2. Rg: compute once, share — approach (B) pre-populate

**Key insight:** Rg computed from naïve P and from bounded P are practically identical
(verified: 36.26 vs 36.26 synthetic, 33.50 vs 33.50 SAMPLE3) because Guinier analysis
uses only the low-q region well below b₁, where coerce_bounds barely touches anything.

**Decision:** Approach **(B)** — pre-populate `self.guinier_objects` in `get_xr_matrices()`
from the naïve P, use them for bounding, and leave them cached so that the existing
`get_guinier_objects()` lazy guard (`if self.guinier_objects is None`) finds them
already set and returns immediately.

**Revised flow in `get_xr_matrices()`:**

```python
def get_xr_matrices(self, debug=False):
    from molass.LowRank.LowRankInfo import compute_lowrank_matrices
    from molass.Guinier.RgEstimator import RgEstimator

    xr = self.xr

    # Step 1: naïve factorization (compute_lowrank_matrices unchanged)
    M_, C_, P, Pe = compute_lowrank_matrices(
        xr.M, self.xr_ccurves, xr.E, self.xr_ranks)

    # Step 2: check if bounded LRF is needed
    ranks = self.xr_ranks or [1] * self.num_components
    has_rank2 = any(r == 2 for r in ranks)

    if has_rank2:
        # Step 3a: compute guinier_objects from naïve P (before bounding)
        if self.guinier_objects is None:
            guinier_objects = []
            for i in range(self.num_components):
                jcurve_array = np.array([xr.qv, P[:,i], Pe[:,i]]).T
                guinier_objects.append(RgEstimator(jcurve_array))
            self.guinier_objects = guinier_objects

        # Step 3b: apply bounded LRF
        from molass.LowRank.BoundedLrf import apply_bounded_lrf
        P, bounded_info = apply_bounded_lrf(
            xr.qv, P, C_, ranks, self.guinier_objects)
        self.bounded_lrf_info = bounded_info

        # Step 3c: re-propagate error for corrected P
        from molass.LowRank.ErrorPropagate import compute_propagated_error
        if xr.E is not None:
            Pe = compute_propagated_error(M_, P, xr.E)

    return M_, C_, P, Pe
```

**How it interacts with `get_guinier_objects()`:**

```python
def get_guinier_objects(self, debug=False):
    if self.guinier_objects is None:                # ← guard
        xr_components = self.get_xr_components()    # triggers get_xr_matrices()
        self.guinier_objects = [c.get_guinier_object() for c in xr_components]
    return self.guinier_objects
```

Two call order scenarios:

1. **`get_xr_matrices()` called first** (rank-2 case):
   - Pre-populates `self.guinier_objects` from naïve P
   - Later, `get_guinier_objects()` sees guard is satisfied → returns immediately

2. **`get_guinier_objects()` called first** (any rank):
   - Guard is `None` → calls `get_xr_components()` → calls `get_xr_matrices()`
   - For rank-2: `get_xr_matrices` sees `self.guinier_objects is None` → populates it
   - Back in `get_guinier_objects`: guard is now satisfied after `get_xr_components()` returns
   - BUT: the list comprehension `[c.get_guinier_object() ...]` overwrites with
     XrComponent-created objects (from corrected P) — same Rg values, different objects
   - This is harmless; the overwrite replaces with equivalent objects

3. **Rank-1 only** (no bounding):
   - `get_xr_matrices()` skips the `has_rank2` block entirely
   - `self.guinier_objects` stays `None`
   - `get_guinier_objects()` populates via the existing path — no change in behavior

**Edge case:** If `XrComponent.get_guinier_object()` is called directly, it creates
a new `RgEstimator` from the corrected P. Same Rg value, redundant but harmless.

### 3. `c1`, `c2` extraction

The concentration values at the peak frame are needed:
```python
j_peak = np.argmax(C[0,:])
c1 = C[0, j_peak]
c2 = C[1, j_peak]    # = c1² for single-component rank-2
```

These are derivable from the `C` matrix already inside `compute_lowrank_matrices`.
Note: `get_xr_matrices` currently returns `C_` (truncated to num_components rows).
The bounding step needs the **full** C (including c² rows). Either:
- Return full C as an extra value, or
- Reconstruct `c2 = c1²` in the bounding step (simpler, since we know rank=2 means quadratic).

We choose the latter — `coerce_bounds` receives `c1` and computes `c2 = c1²` internally.

### 4. Error propagation

After bounding, `P[:,0]` (A(q)) changes due to redistribution:
```
A'(q) = A(q) + (B(q) − B'(q)) · c2/c1
```

The `get_xr_matrices` flow re-calls `compute_propagated_error(M_, P_corrected, E)`
after bounding. The standard formula `Pe = sqrt(E² @ W²)` with `W = pinv(M_) @ P_corrected`
naturally adapts to the modified P.

The sigmoid error correction from legacy `ErrorCorrection.py` is a refinement
that can be added later if needed.

### 5. `get_xr_components()` — the consumer

This method builds `XrComponent` objects from `(C, P, Pe)`:
```python
jcurve_array = np.array([self.xr.qv, xrP[:,i], xrPe[:,i]]).T
```

No change needed here — it already uses whatever P is returned from `get_xr_matrices()`.

### 6. Impact on downstream: model optimization, rigorous decomposition

`optimize_with_model()` and `optimize_rigorously()` use the components from
`get_xr_components()`. They operate on the corrected P, which is the desired behavior.

No changes needed in these methods.

### 7. Impact on `copy_with_new_components()`

This creates a new Decomposition with different ccurves but re-uses `ssd`.
The new decomposition's `bounded_lrf_info` and `guinier_objects` start as `None`
and get recomputed when `get_xr_matrices()` is called — correct behavior.

---

## Files to Create / Modify

| # | File | Action | Lines changed |
|---|------|--------|---------------|
| 1 | `molass/LowRank/BoundedLrf.py` | **Create** | ~80 lines |
| 2 | `molass/LowRank/LowRankInfo.py` | **No change** | — |
| 3 | `molass/LowRank/Decomposition.py` | **Modify** | ~25 lines added |
| 4 | `tests/specific/test_bounded_lrf.py` | **Create** | ~60 lines |

### File 1: `BoundedLrf.py` — Core algorithm

```
estimate_KL(qv, aq, bq, Rg)
    → fit K, L by matching B(q) to -K·Φ(2LR·q)·A(q)
    → refine L for envelope tightness
    → return (K, L, R)

coerce_bounds(qv, aq, bq, c1, c2, L, R)
    → bound = 1/(qv·L·R)²
    → bq_bound = bound · aq/c1
    → clip bq within ±bq_bound
    → A'(q) = A(q) + (B−B')·c2/c1
    → return (P_corrected, bq_bounds, coerced_bq)

apply_bounded_lrf(qv, P, C, ranks, guinier_objects)
    → for each rank-2 component:
        Rg from guinier_objects[k].Rg   ← passed in, not computed here
        K, L, R = estimate_KL(...)
        P_corrected, ... = coerce_bounds(...)
    → return (P_corrected, bounded_info_dict)
```

Dependencies: `molass.SAXS.Theory.SolidSphere.phi` (no Guinier dependency).

### File 2: `LowRankInfo.py` — No change

`compute_lowrank_matrices` remains a pure factorization function.
All bounding orchestration moves to `Decomposition.get_xr_matrices()`.

### File 3: `Decomposition.py` changes

1. In `__init__`: add `self.bounded_lrf_info = None`
2. Rewrite `get_xr_matrices()`: three-step flow
   - Call `compute_lowrank_matrices()` → naïve P
   - Compute `guinier_objects` from naïve P (cache on self)
   - If rank-2: call `apply_bounded_lrf(qv, P, C, ranks, guinier_objects)`
   - Re-propagate error if bounded
   - Return `(M_, C_, P_corrected, Pe)`

### File 4: Tests

Synthetic test verifying:
- `coerce_bounds` clips correctly
- Conservation: `A'·c1 + B'·c2 = A·c1 + B·c2` (row-wise)
- Guinier Rg is preserved

---

## What NOT to Port from Legacy

- `optimize_impl()` — iterative CG optimizer (overkill; coerce_bounds direct clipping suffices)
- `construct_bounds()` — oscillatory node-based approach (replaced by `1/(qLR)²` envelope)
- `SynthesizedLRF.py` — entire file (superseded by Bounded LRF)
- Debug plotting code
- `ErrorCorrection.py` — sigmoid-based error correction (defer to later if standard propagation insufficient)
