# Migration Plan: Unified UV Parameters Architecture

**Version**: 1.1  
**Date**: 2026-07-10 (updated)  
**Status**: Partially Implemented — see status annotations on each Phase  
**Related**: DESIGN_uv_xr_scale_architecture.md, ASSESSMENT_uv_params_across_models.md, Issue #228

---

## Implementation Status Summary (2026-07-10)

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1a: G1400 (LKM) | `uv_cy = uv_w * xr_cy`, `c_inj=1.0` | ✅ Done (prior session) |
| Phase 1b: G1500 (GRM) | Same + R-ordering index `4::2`→`5::2` | ✅ Done (2026-07-10) |
| Phase 1c: G1200/G1100/G1300 (SDM) | `uv_cy = uv_ratio * xr_cy` | ✅ Done (2026-07-13) |
| Phase 2: Legacy estimators | Convert uv_w → ratios | ⏳ Pending |
| Phase 3: Param layout docs | Docstring updates | ⏳ Pending |
| Phase 5: UvOptimizer | `preserve_ratios` parameter | ✅ Done (prior session) — Step 2 bug fixed 2026-07-10 |
| Phase 6: Model upgrades | LKM/GRM pass `preserve_ratios=True` | ✅ Done (prior session) |
| RigorousLkmParams fix | Remove `/ xr_params` (c_inj division) | ✅ Done (2026-07-10) |
| RigorousGrmParams fix | Remove `/ xr_params` (c_inj division) | ✅ Done (2026-07-10) |
| RigorousSdmParams fix | Remove `/ xr_params` division (Phase 1c) | ✅ Done (2026-07-13) |

---

## Goal

Unify the meaning of `uv_params` across all five elution models (SDM, LKM, GRM, EDM, CEDM) to always represent **UV/XR scale ratios** (species property ε_i/k), not absolute UV scales.

---

## Current State

| Model | XR scale computation | UV scale computation | `uv_params` meaning |
|-------|---------------------|---------------------|---------------------|
| SDM, LKM, GRM | `xr_cy = xr_w * pd_cy` | `uv_cy = uv_w * pd_cy` | Absolute UV scale |
| EDM, CEDM | `xr_cy = edm(..., cinj)` | `uv_cy = uv_params[i] * xr_cy` | UV/XR ratio ✓ |

**Problem**: `uv_params` has different meanings, making ratio preservation complex.

---

## Target State

**All models**:
```python
xr_cy = <model-specific XR computation>
uv_cy = uv_params[i] * xr_cy    # ← Unified: ratio × XR curve
```

**`uv_params` definition** (universal): `[ε_0/k, ε_1/k, ..., ε_n/k]` — species properties, model-independent

---

## Benefits

1. **Physical clarity**: `uv_params` always means UV/XR ratio (species property)
2. **Simpler preservation**: Same logic for all models during `upgrade()`
3. **Cleaner bounds**: Ratio bounds (e.g., `[0.1, 1000]`) independent of `xr_w` scale
4. **Fewer parameters**: No redundant `uv_w` when we have `xr_w` and ratio
5. **Easier testing**: One test pattern for ratio preservation across all models

---

## Implementation Plan

### Phase 1: Legacy Objective Functions (molass-legacy)

#### File 1: `molass_legacy/ObjectiveFunctions/G1100.py` (SDM) ✅ DONE (2026-07-13)

**Current code** (lines 93-98):
```python
for xr_w, r_, uv_w in zip(xr_params, rho, uv_params):
    negative_penalty += min(0, xr_w)**2 + min(0, uv_w)**2
    np_ = N*(1 - r_)**me
    tp_ = T_*(1 - r_)**mp
    pd_cy = elutionmodel_func(x_, np_, tp_, N0, t0)
    xr_cy = xr_w * pd_cy
    uv_cy = uv_w * pd_cy
```

**Target code**:
```python
for xr_w, r_, uv_ratio in zip(xr_params, rho, uv_params):
    negative_penalty += min(0, xr_w)**2 + min(0, uv_ratio)**2
    np_ = N*(1 - r_)**me
    tp_ = T_*(1 - r_)**mp
    pd_cy = elutionmodel_func(x_, np_, tp_, N0, t0)
    xr_cy = xr_w * pd_cy
    uv_cy = uv_ratio * xr_cy    # ← Changed: ratio × XR curve
```

**Variable rename**: `uv_w` → `uv_ratio` (clarifies meaning, not strictly necessary)

---

#### File 1b: `molass_legacy/ObjectiveFunctions/G1200.py` (SDM mono+gamma) ✅ DONE (2026-07-13)

Same fix as G1100: `uv_cy = uv_w * pd_cy` → `uv_cy = uv_ratio * xr_cy`. Also removed `_refine_uv_scales` workaround.

Also: `RigorousSdmParams.py` fixed 2026-07-13 — removed `/ xr_params` division. Covers all SDM variants (G1100/G1200/G1300 share this init-params builder).

---

#### File 1c: `molass_legacy/ObjectiveFunctions/G1300.py` (SDM lognormal+gamma) ✅ DONE (2026-07-13)

Same fix: `uv_cy = uv_w * pd_cy` → `uv_cy = uv_ratio * xr_cy`.

---

#### File 2: `molass_legacy/ObjectiveFunctions/G1400.py` (LKM) ✅ DONE

**Actual current code** (already implemented — prior session):
```python
for i, (xr_w, rg_, uv_w) in enumerate(zip(xr_params, rg_params, uv_params)):
    negative_penalty += min(0, xr_w) ** 2 + min(0, uv_w) ** 2
    R_i    = lkmcol_params[3 + 2 * i]
    k_MT_i = lkmcol_params[3 + 2 * i + 1]
    pd_cy  = lkm_pdf(x, Pe, t0, k_MT_i, R_i, c_inj=1.0, t_inj=1.0)  # normalized
    xr_cy  = xr_w * pd_cy
    uv_cy  = uv_w * xr_cy  # ratio × XR already in place
```

**Additional fix (2026-07-10):** `RigorousLkmParams.py` was dividing `uv_params` by `xr_params` (= c_inj) before passing to G1400. Fixed: `uv_params = np.array(uv_params)` (no division).

**Target code**:
```python
for i, (xr_w, rg_, uv_ratio) in enumerate(zip(xr_params, rg_params, uv_params)):
    negative_penalty += min(0, xr_w) ** 2 + min(0, uv_ratio) ** 2
    R_i    = lkmcol_params[3 + 2 * i]
    k_MT_i = lkmcol_params[3 + 2 * i + 1]
    pd_cy  = lkm_pdf(x, Pe, t0, k_MT_i, R_i, c_inj=c_inj, t_inj=1.0)
    xr_cy  = xr_w * pd_cy
    uv_cy  = uv_ratio * xr_cy    # ← Changed: ratio × XR curve
```

---

#### File 3: `molass_legacy/ObjectiveFunctions/G1500.py` (GRM) ✅ DONE

**Actual current code** (already implemented — prior session, plus 2026-07-10 fix):
```python
for i, (xr_w, rg_, uv_w) in enumerate(zip(xr_params, rg_params, uv_params)):
    negative_penalty += min(0, xr_w) ** 2 + min(0, uv_w) ** 2
    R_i     = grmcol_params[5 + 2 * i]
    k_ext_i = grmcol_params[5 + 2 * i + 1]
    a_star_i = (R_i - 1.0) / F_ratio
    pd_cy = grm_pdf(x, Pe, t0, k_ext_i, R_p, D_eff, a_star_i, F_ratio,
                   c_inj=1.0, t_inj=1.0)  # normalized
    xr_cy  = xr_w * pd_cy
    uv_cy  = uv_w * xr_cy  # ratio × XR already in place
```

**Additional fixes (2026-07-10):**
- `RigorousGrmParams.py` was dividing `uv_params` by `xr_params` (= c_inj). Fixed: `uv_params = np.array(uv_params)` (no division).
- **R-ordering index bug**: `grmcol_params[4::2]` extracted `[c_inj, k_ext_0, ...]` instead of `[R_0, R_1, ...]`. Fixed: `grmcol_params[5::2]`. The wrong index caused `order_penalty ≈ 4224` (dominated fv, SV=-100). With fix: `order_penalty=0`, SV=78.29.

**Target code**:
```python
for i, (xr_w, rg_, uv_ratio) in enumerate(zip(xr_params, rg_params, uv_params)):
    negative_penalty += min(0, xr_w) ** 2 + min(0, uv_ratio) ** 2
    R_i     = grmcol_params[5 + 2 * i]
    k_ext_i = grmcol_params[5 + 2 * i + 1]
    a_star_i = (R_i - 1.0) / F_ratio
    pd_cy = grm_pdf(x, Pe, t0, k_ext_i, R_p, D_eff, a_star_i, F_ratio,
                   c_inj=c_inj, t_inj=1.0)
    xr_cy  = xr_w * pd_cy
    uv_cy  = uv_ratio * xr_cy    # ← Changed: ratio × XR curve
```

---

### Phase 2: Parameter Estimators (molass-legacy)

Need to convert initial `uv_w` values to `uv_ratio` values during parameter initialization.

#### File 4: `molass_legacy/Estimators/SdmEstimator.py`

**Current** (lines vary, need to locate):
```python
init_uv_params = [uv_w_0, uv_w_1, uv_w_2]
```

**Target** (add transformation):
```python
init_uv_w = [uv_w_0, uv_w_1, uv_w_2]
init_xr_w = [xr_w_0, xr_w_1, xr_w_2]
init_uv_params = [uv_w_i / xr_w_i for uv_w_i, xr_w_i in zip(init_uv_w, init_xr_w)]
```

**Bounds transformation**:
```python
# Old: bounds_uv_w = [(uv_w_i * 0.1, uv_w_i * 10) for uv_w_i in init_uv_w]
# New:
bounds_uv_params = [(ratio_i * 0.1, ratio_i * 10) for ratio_i in init_uv_params]
# Or simpler: [(0.1, 1000)] for all components (ratio is scale-free)
```

#### File 5: `molass_legacy/Estimators/LkmEstimator.py`

Same pattern as SdmEstimator.

#### File 6: `molass_legacy/Estimators/GrmEstimator.py`

Same pattern as SdmEstimator.

---

### Phase 3: Parameter Layout Managers (molass-legacy)

#### File 7: `molass_legacy/ModelParams/SdmParams.py`

**Current**: Stores and retrieves `uv_w` values (absolute scales)

**Target**: No structural change needed — parameter vector layout unchanged:
```
[xr_w_0, xr_w_1, ..., xr_w_n, ..., uv_params_0, uv_params_1, ..., uv_params_n, ...]
```

Just update docstrings to clarify `uv_params` = ratios, not absolute scales.

**Bound computation** (if present):
```python
# Old (scale-dependent):
uv_bounds = [(uv_init[i] * 0.1, uv_init[i] * 10) for i in range(nc)]

# New (scale-free):
uv_bounds = [(0.1, 1000)] * nc  # Ratios typically in [0.1, 1000] range
```

#### File 8: `molass_legacy/ModelParams/LkmParams.py`

Same as SdmParams.

#### File 9: `molass_legacy/ModelParams/GrmParams.py`

Same as SdmParams.

---

### Phase 4: Library-Side Estimators (molass-library)

Ensure library estimators compute ratios when initializing parameters for rigorous optimization.

#### File 10: `molass/SEC/Models/SdmEstimator.py`

**Check**: Does this compute `uv_params` for legacy path?

If yes:
```python
# Compute initial XR and UV scales
xr_scales = [...]
uv_scales = [...]

# Convert to ratios for legacy optimizer
uv_params = [uv_s / xr_s for uv_s, xr_s in zip(uv_scales, xr_scales)]
```

**Note**: May not be needed if estimator only provides raw values to legacy estimator.

#### File 11: `molass/SEC/Models/LkmEstimator.py`

Same check as SdmEstimator.

#### File 12: `molass/SEC/Models/GrmEstimator.py`

Same check as SdmEstimator.

---

### Phase 5: Library UV Optimizer (molass-library)

This is the PRIMARY fix for the upgrade bug.

#### File 13: `molass/SEC/Models/UvOptimizer.py`

**Current**:
```python
def optimize_uv_decomposition(decomposition, new_xr_ccurves, **kwargs):
    # ...
    def objective_function(params):
        a_, b_ = params[0:2]
        scales_ = params[2:2+num_components]  # ← Fits absolute scales
        # ...
```

**Target**:
```python
def optimize_uv_decomposition(decomposition, new_xr_ccurves, 
                              preserve_ratios=None, **kwargs):
    """
    Parameters
    ----------
    preserve_ratios : array-like or None
        If provided, UV/XR ratios are preserved from previous model.
        Only mapping (a, b) is optimized. If None, ratios are fitted.
    """
    
    if preserve_ratios is not None:
        # Ratio-preservation mode
        def objective_function(params):
            a_, b_ = params  # Only optimize mapping
            mapping = Mapping(a_, b_)
            scales_ = preserve_ratios  # ← Use preserved ratios
            # ... (rest unchanged)
        
        initial_guess = [a, b]
        bounds = [(a_min, a_max), (b_min, b_max)]
    else:
        # Current behavior (fit ratios from scratch)
        def objective_function(params):
            a_, b_ = params[0:2]
            scales_ = params[2:2+num_components]
            # ... (rest unchanged)
        
        initial_guess = [a, b] + initial_scales
        bounds = [(a_min, a_max), (b_min, b_max)] + scale_bounds
    
    result = minimize(objective_function, initial_guess, bounds=bounds)
    # ...
```

---

### Phase 6: Model Upgrade Methods (molass-library)

#### File 14-17: `molass/SEC/Models/SDM.py`, `LKM.py`, `GRM.py`, `EDM.py`

**Current** (all four):
```python
new_uv_ccurves = optimize_uv_decomposition(decomposition, new_xr_ccurves, **kwargs)
```

**Target** (all four):
```python
preserved_ratios = decomposition.get_uv_params()
new_uv_ccurves = optimize_uv_decomposition(
    decomposition, new_xr_ccurves,
    preserve_ratios=preserved_ratios,  # ← NEW
    **kwargs
)
```

---

### Phase 7: Decomposition Class (molass-library)

#### File 18: `molass/LowRank/Decomposition.py`

Add method to extract UV/XR ratios:

```python
def get_uv_params(self):
    """
    Extract UV/XR scale ratios (species properties).
    
    Returns
    -------
    np.ndarray
        Array of UV/XR ratios [ε_0/k, ε_1/k, ..., ε_n/k]
    """
    ratios = []
    for uv_cc in self.uv_ccurves:
        ratios.append(uv_cc.scale)  # UvComponentCurve.scale is the ratio
    return np.array(ratios)
```

**Note**: For Architecture A models (pre-migration), may need to compute ratio:
```python
for uv_cc, xr_cc in zip(self.uv_ccurves, self.xr_ccurves):
    if hasattr(uv_cc, 'scale'):
        ratio = uv_cc.scale  # Architecture B (EDM) or unified
    else:
        # Architecture A (SDM/LKM/GRM pre-migration)
        xr_scale = xr_cc.get_scale_param()
        uv_scale = uv_cc.get_scale_param()
        ratio = uv_scale / xr_scale
    ratios.append(ratio)
```

---

## Parameter Transformation

### Forward Transformation (old → new)

Given old parameter vector with absolute `uv_w`:
```
p_old = [xr_w_0, ..., xr_w_n, ..., uv_w_0, ..., uv_w_n, ...]
```

Compute ratios:
```python
uv_ratios = [uv_w_i / xr_w_i for i in range(n)]
```

New parameter vector:
```
p_new = [xr_w_0, ..., xr_w_n, ..., uv_ratio_0, ..., uv_ratio_n, ...]
```

### Inverse Transformation (new → old)

Given new parameter vector with ratios:
```
p_new = [xr_w_0, ..., xr_w_n, ..., uv_ratio_0, ..., uv_ratio_n, ...]
```

Reconstruct absolute scales:
```python
uv_w = [uv_ratio_i * xr_w_i for i in range(n)]
```

---

## Backward Compatibility

### Option 1: Hard cutover (recommended)

- Apply all changes simultaneously
- No backward compatibility
- Existing `.rig` result folders become incompatible (need re-optimization)
- Users must upgrade both molass-library and molass-legacy together

**Pros**: Clean, no technical debt  
**Cons**: Breaking change

### Option 2: Dual-mode support

- Add `use_uv_ratios` flag to objective functions
- Detect parameter vector structure automatically
- Support both old (absolute) and new (ratio) modes

**Pros**: Gradual migration possible  
**Cons**: Complex, maintains dual code paths

**Recommendation**: Option 1 (hard cutover) — align with JOSS release

---

## Testing Requirements

### Test 1: Ratio computation equivalence

Verify that `uv_ratio * xr_cy == uv_w * pd_cy` when `uv_ratio = uv_w / xr_w`:

```python
def test_ratio_computation_equivalence():
    xr_w, uv_w = 2.055, 2.163
    uv_ratio = uv_w / xr_w  # = 1.053
    pd_cy = lkm_pdf(...)
    
    # Old computation
    xr_cy_old = xr_w * pd_cy
    uv_cy_old = uv_w * pd_cy
    
    # New computation
    xr_cy_new = xr_w * pd_cy
    uv_cy_new = uv_ratio * xr_cy_new
    
    assert np.allclose(uv_cy_old, uv_cy_new)
```

### Test 2: Ratio preservation across upgrades

```python
def test_uv_ratio_preserved_across_upgrades():
    decomp_egh = corrected.quick_decomposition(num_components=3)
    ratios_egh = decomp_egh.get_uv_params()
    
    for model in ['SDM', 'LKM', 'GRM', 'EDM']:
        decomp_upgraded = decomp_egh.upgrade(model=model)
        ratios_upgraded = decomp_upgraded.get_uv_params()
        
        np.testing.assert_allclose(ratios_upgraded, ratios_egh, rtol=0.01,
            err_msg=f"UV/XR ratios changed during {model} upgrade")
```

### Test 3: Rigorous optimization reproduces old results

Run side-by-side comparison:
- Old code: absolute `uv_w` parameters
- New code: `uv_ratio` parameters

Both should reach same objective value (within numerical tolerance).

```python
def test_rigorous_optimization_equivalence():
    # Old implementation
    run_old = decomp_lkm.optimize_rigorously(method='BH', niter=5, ..., _use_old_params=True)
    
    # New implementation (unified ratios)
    run_new = decomp_lkm.optimize_rigorously(method='BH', niter=5, ...)
    
    # Should reach same objective value
    assert abs(run_old.best_fv - run_new.best_fv) < 0.01
```

### Test 4: Bounds scaling

Verify that ratio bounds are scale-independent:

```python
def test_ratio_bounds_scale_independent():
    # Two decompositions with different XR scales
    decomp_a = ...  # XR scales: [0.1, 0.2, 0.3]
    decomp_b = ...  # XR scales: [10, 20, 30] (100× larger)
    
    # Both should give same ratio bounds
    bounds_a = decomp_a.get_uv_param_bounds()
    bounds_b = decomp_b.get_uv_param_bounds()
    
    # Ratios should have same bounds regardless of XR scale
    assert bounds_a == bounds_b  # e.g., [(0.1, 1000)] * 3
```

---

## Rollout Strategy

### Stage 1: Preparation (pre-release)

1. Create feature branch: `feature/unified-uv-params`
2. Implement all changes (Phases 1-7)
3. Run full test suite (all tests pass)
4. Document migration in CHANGELOG

### Stage 2: Testing (pre-release)

1. Test on SAMPLE1-4 datasets
2. Compare results: old vs new implementation
3. Verify SV values match within tolerance
4. Check UV/XR ratio preservation

### Stage 3: Release (with JOSS)

1. Merge to `dev/ongoing-work`
2. Include in next release notes:
   - **Breaking change**: Unified UV parameters
   - Old `.rig` folders incompatible (re-optimization required)
   - Benefits: clearer physics, ratio preservation
3. Update documentation:
   - Tutorial: explain `uv_params` = ratios
   - API docs: clarify parameter meanings

### Stage 4: Verification (post-release)

1. Monitor user feedback
2. Check for any regressions
3. Address issues promptly

---

## Estimated Effort

| Phase | Files | Complexity | Effort |
|-------|-------|------------|--------|
| 1. Objectives | 3 | Low | 2 hours |
| 2. Estimators | 3 | Medium | 4 hours |
| 3. Params | 3 | Low | 2 hours |
| 4. Library estimators | 3 | Low | 2 hours |
| 5. UV optimizer | 1 | Medium | 3 hours |
| 6. Model upgrades | 4 | Low | 1 hour |
| 7. Decomposition | 1 | Low | 1 hour |
| Testing | - | High | 6 hours |
| Documentation | - | Medium | 3 hours |
| **Total** | **18** | - | **24 hours** |

---

## Risk Assessment

### Low Risk
- Mathematical equivalence proven (`uv_ratio * xr_cy == uv_w * pd_cy`)
- Same degrees of freedom
- EDM/CEDM already use this pattern (proven stable)

### Medium Risk
- Breaking change (old results incompatible)
- Requires coordinated update (library + legacy)

### Mitigation
- Thorough testing before release
- Clear migration guide for users
- Release alongside JOSS (natural breaking point)

---

## Success Criteria

1. ✅ All five models use unified `uv_params` definition
2. ✅ UV/XR ratios preserved across all upgrades (test passes)
3. ✅ Rigorous optimization results equivalent to old implementation
4. ✅ No regressions in existing test suite
5. ✅ Documentation updated with new parameter meanings

---

## Next Steps

1. **Approve plan**: Review with user, confirm approach
2. **Create issue**: Track implementation in GitHub
3. **Implement**: Follow phases 1-7 sequentially
4. **Test**: Run comprehensive test suite
5. **Document**: Update all relevant docs
6. **Release**: Merge with next version

---

## References

- Investigation: `experiments/29_five_model_approach/29g_lkm_investigation.ipynb` (cell [16])
- Design: `Copilot/DESIGN_uv_xr_scale_architecture.md`
- Assessment: `Copilot/ASSESSMENT_uv_params_across_models.md`
- Related issues: #228 (Phase 2E), #227 (Scale architecture)
