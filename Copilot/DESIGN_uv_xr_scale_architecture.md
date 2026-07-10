# UV-XR Scale Architecture — Design Document

**Version**: 1.1  
**Date**: 2026-07-10 (updated)  
**Status**: Partially Implemented — see "Current State" section below  
**Related Issues**: #228 (Phase 2E incomplete), #227 (Scale architecture)  
**Migration Plan**: See [MIGRATION_unified_uv_params.md](MIGRATION_unified_uv_params.md) for detailed implementation roadmap

---

## Current State (as of 2026-07-10)

The following were **already implemented** before this document was written (prior session):
- `G1400.py` (LKM): uses `c_inj=1.0` (normalized PDF) and `uv_cy = uv_w * xr_cy` ✅
- `G1500.py` (GRM): uses `c_inj=1.0` (normalized PDF) and `uv_cy = uv_w * xr_cy` ✅
- `UvOptimizer.py`: `preserve_ratios=True` path implemented; LKM/GRM upgrade calls use it ✅

The following **new bugs were found and fixed on 2026-07-10** (during 29g/29h investigation):

| Bug | File | Description | Fix |
|-----|------|-------------|-----|
| LKM UV scale | `RigorousLkmParams.py` | `uv_params = uv_cc.scale / c_inj` (wrong division) | Remove `/ xr_params` |
| GRM UV scale | `RigorousGrmParams.py` | Same pattern as LKM | Remove `/ xr_params` |
| GRM R-ordering | `G1500.py` | `grmcol_params[4::2]` extracted `[c_inj, k_ext_0, ...]` instead of R values | Changed to `[5::2]` |
| UvOptimizer Step 2 | `UvOptimizer.py` | Used `get_scale_param()` (returns c_inj for LKM/GRM) to scale new ratios | Changed to `y.max()` |

**Evidence from 29h notebook (post-fix)**:
- GRM initial SV: **78.29** (was -100.00 with R-ordering bug + UV scale bug)
- UV parameter consistency: all components ratio = **1.000000** (plot_components ↔ score.plot now match)

---

## Executive Summary

UV and XR channels measure the same underlying concentration profiles but with different response factors. XR has a **universal** scale factor (same for all proteins), while UV has **species-specific** extinction coefficients. This physical distinction requires UV curves to be **derived** from XR curves via preserved scale ratios, not independently fitted.

**Status (2026-07-10):** The `preserve_ratios=True` path is now implemented in `UvOptimizer.py` and is used by LKM/GRM upgrades. UV/XR ratios are preserved. The 22× ratio change described below was caused by bugs in `RigorousLkmParams.py`/`RigorousGrmParams.py` (dividing UV scales by c_inj) and a Step 2 error in `UvOptimizer.py` — all now fixed.

---

## Physical Foundation

### 1. XR-universal, UV-specific scaling

| Channel | Formula | Scale Factor |
|---------|---------|--------------|
| X-ray | `XR_i = k × c_i(t)` | `k` universal (electron density ∝ mass) |
| UV | `UV_i = ε_i × c_i(t)` | `ε_i` species-specific (chromophore content) |

### 2. UV as scaled copy of XR

Since both measure the same `c_i(t)`:
```
UV_i(t) = (ε_i/k) × XR_i(t)
```

The ratio `ε_i/k` is a **species property**, independent of elution model (EGH, SDM, LKM, GRM, EDM).

---

## Current Implementation

### Correct parts

`UvComponentCurve` correctly implements UV as derived channel:
```python
class UvComponentCurve(ComponentCurve):
    def get_y(self, x=None):
        x_ = self.mapping.inv(x)  # Map UV frame → XR frame
        return self.scale * self.xr_ccurve.get_y(x_)  # Scaled copy
```

### Bug: UV optimizer re-fits scales

`optimize_uv_decomposition()` minimizes:
```python
minimize ||UV_data - sum(scale_i × XR_i(mapped))||²
```

This treats scales as free variables, ignoring that they should be **preserved** from the previous model.

**Evidence** (from experiments/29_five_model_approach/29g_lkm_investigation.ipynb cell [16]):
```
UV/XR ratios (should be model-independent):
EGH: [ 23.67, 224.87,  47.4 ]   ← Species-specific ε_i/k
LKM: [  1.05,  11.41,   2.16]   ← Changed 22×! Physical violation
Change: [0.045, 0.051, 0.046]   ← Should be [1, 1, 1]
```

---

## Design Solution

### Core principle

`uv_params` = UV/XR scale ratios = `[ε_0/k, ε_1/k, ..., ε_n/k]`

These are **optimization parameters** with special properties:
- Computed once during initial `quick_decomposition()`
- **Preserved** across all `upgrade()` calls (species property)
- Can be refined during rigorous optimization (starting from preserved values)

### Workflow

#### Initial decomposition
```python
quick_decomposition():
    1. Decompose XR → xr_ccurves
    2. Compute uv_params = UV/XR ratios (species properties)
    3. Build uv_ccurves = UvComponentCurve(mapping, xr_ccurves, uv_params)
    4. Store uv_params in Decomposition object
```

#### Upgrade (e.g., EGH → LKM)
```python
decomp.upgrade(model='LKM'):
    1. New XR model: xr_ccurves → new_xr_ccurves
       - XR scales change (H → c_inj, 21× jump) ✓
    
    2. UV follows with PRESERVED ratios:
       - uv_params_preserved = decomp.get_uv_params()
       - mapping refined (UV/XR frame alignment only)
       - new_uv_ccurves = UvComponentCurve(mapping, new_xr_ccurves, uv_params_preserved)
       - UV/XR ratios unchanged ✓
```

#### Rigorous optimization
```python
optimize_rigorously():
    1. Both xr_params and uv_params are free parameters
    2. But uv_params initialized from PRESERVED values (not re-fitted)
    3. Optimizer refines both (but starting point respects species properties)
```

---

## Implementation Plan

### 1. Add `get_uv_params()` method to Decomposition

**Location**: `molass/LowRank/Decomposition.py`

```python
def get_uv_params(self):
    """
    Extract UV/XR scale ratios from current component curves.
    
    Returns
    -------
    np.ndarray
        Array of UV/XR ratios [ε_0/k, ε_1/k, ..., ε_n/k] (species properties)
    """
    ratios = []
    for uv_cc, xr_cc in zip(self.uv_ccurves, self.xr_ccurves):
        # UvComponentCurve.scale is the UV/XR ratio
        ratios.append(uv_cc.scale)
    return np.array(ratios)
```

### 2. Modify `optimize_uv_decomposition()`

**Location**: `molass/SEC/Models/UvOptimizer.py`

**Add parameter**: `preserve_ratios=None`

```python
def optimize_uv_decomposition(decomposition, xr_ccurves, preserve_ratios=None, **kwargs):
    """
    Optimize UV decomposition based on XR component curves.
    
    Parameters
    ----------
    preserve_ratios : array-like or None
        If provided, preserve these UV/XR ratios (only optimize mapping).
        If None, fit ratios from scratch (backward compatibility).
    """
    if preserve_ratios is not None:
        # Mode A: Preserve species-specific ratios, only optimize mapping
        bounds = [(a*0.8, a*1.2), (b-dx, b+dx)]  # Only a, b
        initial_guess = [a, b]
        
        def objective_function(params):
            a_, b_ = params
            mapping = Mapping(a_, b_)
            cy_list = []
            for xr_ccurve, ratio in zip(xr_ccurves, preserve_ratios):
                uv_ccurve = UvComponentCurve(x, mapping, xr_ccurve, ratio)
                cy = uv_ccurve.get_y()
                cy_list.append(cy)
            ty = np.sum(cy_list, axis=0)
            return np.sum((y - ty)**2)
    else:
        # Mode B: Original behavior (fit scales from scratch)
        # [current implementation unchanged]
```

### 3. Update all model `optimize_decomposition()` methods

**Files to modify**:
- `molass/SEC/Models/LKM.py`
- `molass/SEC/Models/GRM.py`
- `molass/SEC/Models/SDM.py`
- `molass/SEC/Models/EDM.py`
- `molass/SEC/Models/CEDM.py`

**Pattern**:
```python
def optimize_decomposition(decomposition, **kwargs):
    # ... optimize XR ...
    
    if not xr_only:
        # Preserve UV/XR ratios from input decomposition
        preserved_ratios = decomposition.get_uv_params()
        new_uv_ccurves = optimize_uv_decomposition(
            decomposition, new_xr_ccurves, 
            preserve_ratios=preserved_ratios,  # ← NEW
            **kwargs
        )
    
    return decomposition.copy_with_new_components(new_xr_ccurves, new_uv_ccurves)
```

### 4. Add test for ratio preservation

**Location**: `tests/generic/` or `tests/specific/SEC/Models/`

```python
def test_uv_xr_ratio_preserved_across_upgrades():
    """Verify UV/XR ratios (species properties) unchanged by model upgrades."""
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    
    ssd = SSD(SAMPLE1)
    trimmed = ssd.trimmed_copy()
    corrected = trimmed.corrected_copy()
    
    # Initial decomposition
    decomp_egh = corrected.quick_decomposition(num_components=3)
    ratios_egh = decomp_egh.get_uv_params()
    
    # Upgrade to LKM
    decomp_lkm = decomp_egh.upgrade(model='LKM')
    ratios_lkm = decomp_lkm.get_uv_params()
    
    # Assert ratios preserved (species property, not model property)
    np.testing.assert_allclose(ratios_lkm, ratios_egh, rtol=0.01,
        err_msg="UV/XR ratios changed during upgrade (species violation)")
    
    # Verify XR scales DID change (model-specific)
    xr_scales_egh = [cc.get_scale_param() for cc in decomp_egh.xr_ccurves]
    xr_scales_lkm = [cc.get_scale_param() for cc in decomp_lkm.xr_ccurves]
    assert not np.allclose(xr_scales_lkm, xr_scales_egh, rtol=0.1), \
        "XR scales should change during upgrade (H → c_inj)"
```

---

## Impact Assessment

### Fixes
- **Issue #228**: Ensures UV scales behave consistently with XR scales during upgrades
- **Physical correctness**: UV/XR ratios now respect species-independence
- **Rigorous optimization**: Better initial guesses for `uv_params`

### Breaking changes
- **None** — `preserve_ratios=None` maintains backward compatibility

### Performance
- **Neutral** — Same number of optimizer calls, fewer free variables in UV fit

---

## References

- Investigation notebook: `experiments/29_five_model_approach/29g_lkm_investigation.ipynb`
- Original architecture insight: User discussion 2026-07-09
- Related memory: `/memories/repo/uv-xr-scale-architecture.md`
