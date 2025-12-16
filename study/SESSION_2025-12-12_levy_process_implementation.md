# Session Summary: Lévy Process Framework for Chromatography (Dec 12, 2024)

## Objectives
1. Debug and fix FFT inversion issues in Lévy process chromatography demonstrations
2. Understand theoretical foundation from Pasti 2005 and Dondi 2002 papers
3. Prepare for re-implementing molass SDM using proper Lévy characteristic function approach
4. Fix visualization issues and improve demonstration clarity

## Key Problems Solved

### 1. Negative Values in FFT Inversion
**Problem**: `peak_levy` had negative values, which is impossible for probability densities.

**Root Cause**: Incorrect FFT sign convention. The characteristic function φ(ω) = E[exp(+iωt)] uses positive exponent, but NumPy's `ifft` uses exp(-iωt).

**Solution**: 
- Use `np.fft.fftfreq()` for proper symmetric frequency array
- Apply `np.conj(cf)` before `ifft` to match conventions
- Remove `ifftshift`/`fftshift` operations that caused artifacts
- Final form: `peak = np.fft.ifft(np.conj(cf)).real / dt`

**Files Fixed**:
- `levy_vs_montecarlo_demo.py`: Fixed `levy_fft_method()`
- `pasti2005_levy_inversion.py`: Fixed `invert_cf_fft()`

### 2. Peak Ordering Reversed
**Problem**: Peaks appeared in wrong time order (fastest eluting last).

**Solution**: The conjugate fix (`np.conj(cf)`) corrected the time direction.

### 3. Visualization Improvements
**Problem**: Two-panel plot in `example_case_B()` was redundant.

**Solution**: Simplified to single comprehensive plot showing:
- All three peaks (NS only, S only, combined) in retention time coordinates
- Shaded region for mobile phase (tM = 30s)
- Complete statistics in one view

## Theoretical Insights

### Papers Read
1. **Dondi 2002**: Classification of general elution chromatography (GEC) models
   - Monopore: Single distribution of sorption times
   - Two-pore (bipore): NS (nonspecific) + S (specific) sites
   - Multipore: Multiple distinct sorption time distributions

2. **Pasti 2005**: Lévy process framework connecting single-molecule to ensemble
   - Discrete sorption time distribution {τS,i, ΔF(τS,i)} from single-molecule studies
   - Characteristic function: φ(ω) = exp[r̄M * Σ(exp(iω*τS,i) - 1) * ΔF(τS,i)]
   - FFT inversion yields chromatographic peak shape
   - Multiple independent processes combine via CF multiplication

### Key Equations Implemented
```python
# Characteristic function for discrete distribution
cf = np.exp(rM * np.sum((np.exp(1j * omega[:, None] * tauS_i) - 1) * DeltaF, axis=1))

# Inversion to time domain
peak = np.fft.ifft(np.conj(cf)).real / dt
time = np.arange(len(cf)) * dt
```

### Chromatography Context
- **Retention factor**: k' = tS/tM
- **SEC (Size Exclusion)**: k' ≈ 0 (minimal stationary phase interaction)
- **Adsorption HPLC**: k' = 2-5 typical
- **Total retention time**: tR = tM + tS

## Code Changes Summary

### `levy_vs_montecarlo_demo.py`
- Fixed `levy_fft_method()` to use `fftfreq` and proper conjugate

### `pasti2005_levy_inversion.py`
- **`levy_cf_discrete()`**: Computes CF from {τS,i, ΔF(τS,i)}
- **`invert_cf_fft()`**: Clean FFT inversion (multiple iterations to fix)
- **`calculate_chromatographic_peak()`**: Wrapper for full calculation
- **`example_case_A()`**: λ-DNA with varying rM showing peak splitting
- **`example_case_B()`**: DiI dye NS+S sites, simplified to single plot

### Key Parameters Used
```python
# Case B: DiI dye
tauS_i_S = [160, 320, 480, 640, 800, 2240, 2720, 3360] ms  # Specific sites
tauS_i_NS = [68] ms  # Nonspecific sites  
p = 0.01  # Fraction of specific sites
rM_total = 1000  # Total adsorption events
tM = 30 s  # Mobile phase time (for visualization)
```

## Technical Details

### Python Environment
- Switched from Python 3.12 → 3.13 to access pypdf library
- Key packages: numpy, matplotlib, scipy

### FFT Configuration
```python
n_points = 8192  # High resolution
dt = total_mean / n_points * 6  # Time spacing
omega = np.fft.fftfreq(n_points, dt) * 2 * np.pi
```

### Common Pitfalls Avoided
- ❌ Complex mirroring/shifting schemes → artifacts
- ❌ Center of mass rolling → introduced artifacts  
- ❌ Using `ifftshift` → broke periodicity
- ✅ Simple `ifft(conj(cf)).real / dt` works best

## Connection to molass Library

### Current SDM Implementation
**Location**: `molass/SEC/Models/SDM.py`, `molass/SEC/Models/SdmEstimator.py`

**Current Approach**: Empirical moment matching
- Parameters: N, T, N0, t0, poresize with power law exponents
- `estimate_sdm_column_params()` fits mean/variance

### Proposed Re-implementation
**Goal**: Replace empirical approach with Lévy CF framework

**Key Differences**:
- Old: Fit parameters to match moments
- New: Extract {τS,i, ΔF(τS,i)} directly from data via CF fitting
- Better: Physical interpretation of sorption time distributions
- Advantage: Can handle multiple populations naturally (NS+S sites)

### Next Steps for SDM Re-implementation
1. Design CF-based fitting procedure for SEC-SAXS elution curves
2. Extract discrete sorption time distributions from experimental data
3. Replace `SdmEstimator` with Lévy-aware version
4. Test on real `decomposition.xr_ccurves` data
5. Compare results with current empirical SDM

## Files Created/Modified

### Modified
- `study/src/levy_vs_montecarlo_demo.py` - Fixed FFT inversion
- `study/src/pasti2005_levy_inversion.py` - Multiple fixes and simplification

### Created
- `study/pasti2005_case_A_rM_comparison.png` - λ-DNA peak splitting demo
- `study/pasti2005_case_B_peak.png` - DiI dye NS+S sites demo

### Reference Papers (in study directory)
- `2002, Francesco Dondi.pdf` - GEC model classification
- `2005, Francesco Pasti.pdf` - Lévy single-molecule framework

## Important Concepts for Future Reference

### Lévy Process Framework
- **Single-molecule → Ensemble**: Discrete distribution at molecular level + Poisson sampling → continuous chromatographic peak
- **CF Multiplication**: Independent processes combine via φ_total = φ_1 × φ_2 × ...
- **FFT Inversion**: Fast numerical method to obtain peak shapes

### For SEC-SAXS Application
- SEC has k' ≈ 0, so mostly tM with small dispersive corrections
- Stochastic dispersion from:
  - Flow velocity variations
  - Diffusion in/out of pores
  - Non-ideal SEC column behavior
- Can use multi-population model if needed (different molecular species)

## Questions for Next Session
1. How to fit experimental SEC-SAXS curves to extract {τS,i, ΔF(τS,i)}?
2. What is the interpretation of "sorption time" in SEC context (non-adsorbing)?
3. Should we use continuous distribution F(τS) instead of discrete for SEC?
4. How to integrate with existing molass decomposition workflow?
5. Validation strategy: compare Lévy-SDM vs current empirical SDM on real data

## Visualization Improvements Made
- ✅ Single comprehensive plot for case B
- ✅ Shaded mobile phase region for clarity
- ✅ Increased tM from 6s → 30s for better visibility
- ✅ Combined statistics showing events and retention times
- ✅ Clear peak ordering (S only → NS only → combined)

## Status at End of Session
- ✅ FFT inversion fully debugged and working
- ✅ Theoretical foundation understood from papers
- ✅ Demonstration code clean and functional
- ⏸️ Ready to begin SDM re-implementation in next session
