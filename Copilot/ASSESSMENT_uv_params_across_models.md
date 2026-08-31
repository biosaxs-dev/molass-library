# UV Parameters Architecture Assessment — All Models

**Date**: 2026-07-09  
**Context**: Investigation of UV/XR scale handling across five SEC elution models  
**Migration Plan**: See [MIGRATION_unified_uv_params.md](MIGRATION_unified_uv_params.md) for unification roadmap

---

## Summary of Findings

**Two distinct architectures exist:**

| Architecture | Models | XR scale | UV scale | UV/XR ratio |
|--------------|--------|----------|----------|-------------|
| **A: Explicit** | SDM, LKM, GRM | `xr_w[i]` (explicit) | `uv_w[i]` (explicit) | `uv_w[i] / xr_w[i]` |
| **B: Embedded** | EDM, CEDM | `cinj[i]` (embedded) | `uv_params[i]` (ratio) | `uv_params[i]` directly |

**Critical bug:** All models re-fit UV parameters during `upgrade()`, violating the species-independence principle.

---

## Detailed Analysis by Model

### 1. Initial Decomposition (EGH baseline)

**Location**: `molass/Decompose/Partner.py::decompose_from_partner()`

**Method**:
1. Map XR EGH shapes to UV frames using mapping (a, b)
2. Fit UV heights via `minimize()` (shape parameters fixed from XR)
3. Create `UvComponentCurve` with `scale = uv_height / xr_height`

**Result**: `UvComponentCurve.scale` = UV/XR ratio (species property, ε_i/k)

**Status**: ✓ **Correct** — initial ratios computed from physics

---

### 2. SDM (Stochastic Dispersive Model)

#### Library upgrade path

**File**: `molass/SEC/Models/SDM.py::optimize_decomposition()`

**Lines 99-100**:
```python
from molass.SEC.Models.UvOptimizer import optimize_uv_decomposition
new_uv_ccurves = optimize_uv_decomposition(decomposition, new_xr_ccurves, **kwargs)
```

**Status**: ❌ **Bug** — No `preserve_ratios` parameter, re-fits UV from scratch

#### Rigorous optimization (legacy)

**File**: `molass_legacy/ObjectiveFunctions/G1100.py`

**Lines 97-98**:
```python
xr_cy = xr_w * pd_cy
uv_cy = uv_w * pd_cy
```

**Architecture**: **Explicit scale (A)**
- `xr_params` = `[xr_w_0, xr_w_1, ..., xr_w_n]` (explicit XR scales)
- `uv_params` = `[uv_w_0, uv_w_1, ..., uv_w_n]` (explicit UV scales)
- UV/XR ratio = `uv_w_i / xr_w_i` (computed from two separate parameters)

**Status**: ✓ **Architecture correct** — but initial values from upgrade are wrong (ratios not preserved)

---

### 3. LKM (Lumped Kinetic Model)

#### Library upgrade path

**File**: `molass/SEC/Models/LKM.py::optimize_decomposition()`

**Lines 64-66**:
```python
from molass.SEC.Models.UvOptimizer import optimize_uv_decomposition
new_uv_ccurves = optimize_uv_decomposition(
    decomposition, new_xr_ccurves, **kwargs)
```

**Status**: ❌ **Bug** — No `preserve_ratios` parameter, re-fits UV from scratch

#### Rigorous optimization (legacy)

**File**: `molass_legacy/ObjectiveFunctions/G1400.py` ✅ ALREADY FIXED (prior session)

**Actual current code**:
```python
pd_cy = lkm_pdf(x, Pe, t0, k_MT_i, R_i, c_inj=1.0, t_inj=1.0)  # normalized
xr_cy = xr_w * pd_cy
uv_cy = uv_w * xr_cy  # ratio × XR
```

**Architecture**: **Explicit scale (A)** — no double-scaling (c_inj=1.0 removes it)
- `xr_params` = `[xr_w_0, xr_w_1, ..., xr_w_n]` = c_inj values (explicit scales)
- `uv_params` = `[uv_w_0, uv_w_1, ..., uv_w_n]` = UV/XR ratios (= `uv_cc.scale` directly)
- UV/XR ratio = `uv_w_i / xr_w_i`
- **Problem**: `lkm_pdf()` with `c_inj` already includes concentration scaling
  - `pd_cy = c_inj × (kinetic_pdf)`
  - `xr_cy = xr_w × (c_inj × kinetic_pdf)` ← Double-scaling!
  - Both `c_inj` and `xr_w` act as scale parameters

**Status**: ⚠️ **Double-scaling** — Redundant parameters (`c_inj` shared, `xr_w` per-component)

**Related**: Issue #228 (Phase 2E incomplete)

---

### 4. GRM (General Rate Model)

#### Library upgrade path

**File**: `molass/SEC/Models/GRM.py`

**Lines 76-77**:
```python
from molass.SEC.Models.UvOptimizer import optimize_uv_decomposition
new_uv_ccurves = optimize_uv_decomposition(...)
```

**Status**: ❌ **Bug** — No `preserve_ratios` parameter, re-fits UV from scratch

#### Rigorous optimization (legacy)

**File**: `molass_legacy/ObjectiveFunctions/G1500.py` ✅ FIXED (2026-07-10)

**Actual current code**:
```python
pd_cy = grm_pdf(x, Pe, t0, k_ext_i, R_p, D_eff, a_star_i, F_ratio,
               c_inj=1.0, t_inj=1.0)  # normalized
xr_cy = xr_w * pd_cy
uv_cy = uv_w * xr_cy  # ratio × XR
```

**Architecture**: **Explicit scale (A)** — no double-scaling (c_inj=1.0)
- `uv_params` = UV/XR ratios = `uv_cc.scale` values directly ✓

**Status**: ✅ **Fixed (2026-07-10)** — Three bugs corrected:
1. `RigorousGrmParams.py`: divided UV scales by c_inj → removed division
2. `G1500.py` R-ordering: `grmcol_params[4::2]` extracted wrong elements (c_inj + k_ext instead of R values) → changed to `grmcol_params[5::2]`. Effect: `order_penalty ≈ 4224` → `0`, SV=-100 → 78.29
3. `UvOptimizer.py` Step 2: used `get_scale_param()` (= c_inj) instead of `y.max()` for ratio scaling → changed to `y.max()`

---

### 5. EDM (Equilibrium Dispersive Model)

#### Library upgrade path

**File**: `molass/SEC/Models/EDM.py`

**Lines 47, 63**:
```python
from molass.SEC.Models.UvOptimizer import optimize_uv_decomposition
# ...
new_uv_ccurves = optimize_uv_decomposition(decomposition, new_xr_ccurves, **kwargs)
```

**Status**: ❌ **Bug** — No `preserve_ratios` parameter, re-fits UV from scratch

#### Rigorous optimization (legacy)

**File**: `molass_legacy/ObjectiveFunctions/G2010.py`

**Lines 87-88**:
```python
for t0, u, a, b, e, Dz, cinj in xr_params:
    xr_cy = edm_impl(x, t0, u, a, b, e, Dz, cinj)
    uv_cy = uv_params[k] * xr_cy
```

**Architecture**: **Embedded scale (B)**
- `xr_params` = `[(t0_0, u_0, a_0, b_0, e_0, Dz_0, cinj_0), ...]` (per-component cinj)
- `uv_params` = `[ratio_0, ratio_1, ..., ratio_n]` (UV/XR ratios directly)
- UV curve = `uv_params[i] × xr_curve[i]` (simple multiplication)

**Status**: ✓ **Architecture clean** — but initial values from upgrade are wrong (ratios not preserved)

**Note**: EDM uses **per-component cinj**. This is mathematically equivalent to LKM/GRM **shared c_inj + fractions**:
- Per-component: `c_inj = [c_0, c_1, c_2]` (3 DOF)
- Shared + fractions: `c_inj × [f_0, f_1, f_2]` with `sum(f) = 1` (3 DOF)
- Both span the same parameter space. Per-component form is arguably simpler (no sum constraint).

---

### 6. CEDM (Coupled EDM)

#### Library upgrade path

**Status**: No separate `CEDM.py` class — handled within EDM.py or legacy only

#### Rigorous optimization (legacy)

**File**: `molass_legacy/ObjectiveFunctions/G2020.py`

**Lines 104-113**:
```python
for a_k, b_k, cinj_k in xr_params_abc:
    full = np.array([t0_sh, u_sh, a_k, b_k, e_sh, Dz_sh, cinj_k])
    xr_cy = np.nan_to_num(edm_impl(x, *full), nan=0.0, posinf=0.0, neginf=0.0)
    uv_cy = uv_params[len(xr_cy_list)] * xr_cy
```

**Architecture**: **Embedded scale (B)** + **Shared column parameters**
- Column params: `[t0_sh, u_sh, e_sh, Dz_sh]` (shared across components)
- Component params: `[a_k, b_k, cinj_k]` (per-component, cinj embedded)
- `uv_params` = `[ratio_0, ratio_1, ..., ratio_n]` (UV/XR ratios)

**Status**: ✓ **Architecture clean** — but initial values from upgrade are wrong (ratios not preserved)

---

## UV Optimizer Implementation

**File**: `molass/SEC/Models/UvOptimizer.py::optimize_uv_decomposition()`

**Current behavior**:
```python
def objective_function(params):
    a_, b_ = params[0:2]
    mapping = Mapping(a_, b_)
    scales_ = params[2:2+num_components]  # ← Fits scales from scratch
    # ...
    return error

initial_guess = [a, b] + initial_scales
result = minimize(objective_function, initial_guess, bounds=bounds)
```

**Problem**: Treats `scales` as free variables, ignoring that they should be **preserved** from initial decomposition

**Effect**: UV/XR ratios change 22× during upgrade (demonstrated in 29g notebook cell [16])

---

## Architecture Inconsistency

### Problem 1: Two incompatible scale architectures

**Architecture A** (SDM, LKM, GRM):
- Both XR and UV have explicit scale parameters
- Ratio = `uv_w / xr_w` (derived from two parameters)

**Architecture B** (EDM, CEDM):
- XR scale embedded in `cinj`
- UV scale is the ratio itself

**Consequence**: Cannot have a single `preserve_ratios` implementation that works for both

### Problem 2: XR scale redundancy (LKM/GRM only)

**EDM per-component** vs **LKM/GRM shared**:
- **Mathematical equivalence**: Both parameterizations have 3 DOF for 3 components
  - Per-component: `c_inj = [5, 2, 3]` (unconstrained)
  - Shared + fractions: `c_inj = 10`, `f = [0.5, 0.2, 0.3]` with `sum(f) = 1` (constrained)
- **Not a bug**: Just different parameterization choices

**LKM/GRM redundancy** (the actual issue):
- Have BOTH `c_inj` (shared) AND `xr_w` (per-component) multipliers
- `xr_cy = xr_w[i] × (c_inj × pdf)` — double-scaling
- 4 parameters for 3 DOF → redundancy

---

## Recommended Fix Strategy

### Phase 1: Preserve ratios during upgrade (all models)

**Goal**: Stop re-fitting UV parameters from scratch

**Implementation**:
1. Add `get_uv_xr_ratios()` method to `Decomposition`
   - For Architecture A: compute `uv_w / xr_w` for each component
   - For Architecture B: extract `uv_params` directly
2. Modify `optimize_uv_decomposition()` to accept `preserve_ratios` parameter
3. Update all five model `optimize_decomposition()` methods to pass preserved ratios
4. Add test: assert `ratio_after ≈ ratio_before` for all models

**Priority**: HIGH — Fixes physical violation (species-independence)

### Phase 2: Unify scale architecture (post-JOSS)

**Goal**: Resolve Architecture A vs B inconsistency

**Option 2a: Move Architecture A → B**
- SDM, LKM, GRM adopt embedded scale (like EDM)
- Remove explicit `xr_w` / `uv_w` parameters
- `uv_params` becomes ratios for all models

**Option 2b: Keep dual architecture, document difference**
- Architecture A (explicit): phenomenological/stochastic models
- Architecture B (embedded): kinetic models with physical c_inj
- Document the distinction, accept the complexity

**Priority**: MEDIUM — Architectural cleanup, not a physical violation

### Phase 3: Resolve LKM/GRM double-scaling (related to issue #228)

**Goal**: Remove `xr_w` multiplier redundancy

**Implementation**:
- Keep `c_inj` (shared) as the scale parameter
- Add per-component `fraction[i]` to replace `xr_w[i]`
- `xr_cy = c_inj × fraction[i] × kinetic_pdf(...)`
- Constraint: `sum(fraction) = 1.0`

**Priority**: MEDIUM — Related to Phase 2E cleanup

---

## Testing Requirements

### Test 1: Ratio preservation across upgrades
```python
def test_uv_xr_ratio_preserved_across_upgrades():
    decomp_egh = corrected.quick_decomposition(num_components=3)
    ratios_egh = decomp_egh.get_uv_xr_ratios()
    
    for model in ['SDM', 'LKM', 'GRM', 'EDM']:
        decomp_upgraded = decomp_egh.upgrade(model=model)
        ratios_upgraded = decomp_upgraded.get_uv_xr_ratios()
        
        np.testing.assert_allclose(ratios_upgraded, ratios_egh, rtol=0.01,
            err_msg=f"UV/XR ratios changed during {model} upgrade")
```

### Test 2: Architecture A ratio calculation
```python
def test_architecture_a_ratio_computation():
    """For SDM/LKM/GRM: verify ratio = uv_w / xr_w"""
    decomp = corrected.quick_decomposition().upgrade(model='SDM')
    
    for i, (xr_cc, uv_cc) in enumerate(zip(decomp.xr_ccurves, decomp.uv_ccurves)):
        xr_scale = xr_cc.params[0]  # Explicit scale
        uv_scale = uv_cc.params[0]  # Explicit scale
        ratio_computed = uv_scale / xr_scale
        ratio_direct = uv_cc.scale
        
        np.testing.assert_allclose(ratio_computed, ratio_direct, rtol=1e-6)
```

### Test 3: Architecture B ratio storage
```python
def test_architecture_b_ratio_storage():
    """For EDM/CEDM: verify uv_params = ratios directly"""
    decomp = corrected.quick_decomposition().upgrade(model='EDM')
    
    for i, uv_cc in enumerate(decomp.uv_ccurves):
        # For embedded scale architecture, scale IS the ratio
        assert uv_cc.scale == decomp.get_uv_xr_ratios()[i]
```

---

## References

- Investigation notebook: `experiments/29_five_model_approach/29g_lkm_investigation.ipynb`
- Design document: `Copilot/DESIGN_uv_xr_scale_architecture.md`
- Memory: `/memories/repo/uv-xr-scale-architecture.md`
- Related issues: #228 (Phase 2E incomplete), #227 (Scale architecture)
