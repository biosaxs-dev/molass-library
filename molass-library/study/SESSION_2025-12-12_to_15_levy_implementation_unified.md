# Unified Session Summary: Lévy Process Implementation for SEC (Dec 12-16, 2024)

## Objectives

1. Implement Lévy characteristic function framework for SEC stochastic modeling
2. Validate against Giddings-Eyring-Carmichael (1955) analytical theory
3. Understand numerical differences between FFT inversion methods
4. Prepare foundation for multi-site and continuous distribution models

## Key Theoretical Foundation

### Papers Reviewed

1. **Giddings, Eyring, Carmichael (1955):** Stochastic SEC theory
   - Poisson-distributed pore visits (mean np)
   - **Exponentially-distributed** residence times (mean τp)
   - Analytical PDF with modified Bessel function I₁

2. **Pasti et al. (2005):** Lévy process single-molecule framework
   - Characteristic function: φ(ω) = exp[r̄M * Σ(exp(iω*τS,i) - 1) * ΔF(τS,i)]
   - FFT inversion for chromatographic peak shapes
   - Independent processes combine via CF multiplication

3. **Sepsey et al. (2014):** Lognormal pore size distribution extension
   - Integration over continuous distributions
   - Characteristic function approach for polydisperse systems

4. **Witkovský (2018):** Gil-Pelaez inversion formula
   - Adaptive grid selection: δt = 2π/(B-A), six-sigma rule
   - Trapezoidal quadrature: pdf(y) ≈ (δt/π) Σ wⱼ Re(e^(-itⱼy) φ(tⱼ))
   - Superior numerical accuracy compared to simple FFT

### Compound Poisson Process Variance

**Critical insight:** For compound Poisson with event size distribution X:
```
Var[total] = λ × E[X²]  (NOT λ × Var[X])
```

For exponential distribution with mean τp:
- E[X] = τp
- Var[X] = τp²
- E[X²] = 2τp² (key!)
- Therefore: **Var[total] = np × 2τp²**

## Correct Characteristic Function Formulation

### Individual Event Distribution

**WRONG:** Delta function (deterministic duration)
```python
φ(ω) = exp[np × (exp(iω·τp) - 1)]
# This gives variance = np·τp² (half of correct value!)
```

**CORRECT:** Exponential distribution (Giddings model)
```python
λ = 1/τp
φ_X(ω) = λ / (λ - iω)  # CF of exponential(τp)
φ(ω) = exp[np × (φ_X(ω) - 1)]
# This gives variance = np·2τp² ✓
```

### Multi-Site Extension

```python
# Nonspecific (NS) and Specific (S) sites
lambda_NS = 1.0 / tau_NS
lambda_S = 1.0 / tau_S

phi_NS = lambda_NS / (lambda_NS - 1j * omega)
phi_S = lambda_S / (lambda_S - 1j * omega)

cf = np.exp(r_NS * (phi_NS - 1) + r_S * (phi_S - 1))
```

### Continuous Distribution Integration

```python
# For lognormal pore size distribution
for tau, deltaF in zip(tau_values, deltaF_values):
    lambda_exp = 1.0 / tau
    phi_X = lambda_exp / (lambda_exp - 1j * omega)
    sum_term += (phi_X - 1) * deltaF

cf = np.exp(rM_bar * sum_term)
```

## FFT Inversion Methods Comparison

### Method 1: Simple FFT (Manual Implementation)

```python
def levy_monopore_pdf(t, np_, tp_, n_points=8192):
    """Simple fixed-grid FFT inversion."""
    # Fixed grid spacing
    expected_mean = np_ * tp_
    dt = expected_mean / n_points * 4
    
    # Frequency array
    omega = np.fft.fftfreq(n_points, dt) * 2 * np.pi
    
    # Characteristic function
    lambda_exp = 1.0 / tp_
    phi_X = lambda_exp / (lambda_exp - 1j * omega)
    cf = np.exp(np_ * (phi_X - 1))
    
    # IFFT inversion
    peak = np.fft.ifft(cf).real
    peak = np.fft.ifftshift(peak)
    
    # Ensure non-negative BEFORE normalizing
    peak = np.maximum(peak, 0)
    peak = peak / (np.sum(peak) * dt)
    
    return pdf
```

**Characteristics:**
- Fixed grid: dt = μ/(n_points × 4)
- Simple `ifft` without phase correction
- Max error vs analytical: ~0.003
- Moments: Mean=100.0000, Var=200.0002 ✓

### Method 2: Gil-Pelaez Formula (Legacy FftInvPdf)

```python
# molass_legacy.SecTheory.SecPDF.FftInvPdf
# Based on Witkovský (2018) Gil-Pelaez formula:
# pdf(y) ≈ (δt/π) Σ wⱼ Re(e^(-itⱼy) φ(tⱼ))
```

**Characteristics:**
- Adaptive grid: δt = 2π/(B-A), six-sigma rule (A,B) = μ ± 6σ
- Trapezoidal quadrature weights: w₀ = w_N = 1/2, else wⱼ = 1
- Automatic domain selection based on distribution moments
- Max error vs analytical: ~0 (machine precision)
- Moments: Mean=100.0000, Var=200.0000 ✓

### Numerical Accuracy Comparison

| Method | Max Error | Var Error | Implementation |
|--------|-----------|-----------|----------------|
| GEC Bessel (analytical) | - | - | Exact |
| Simple FFT | 0.003 | 0.0002 | Fixed grid |
| Gil-Pelaez (legacy) | ~0 | ~0 | Adaptive grid |

**Key insight:** Both methods are theoretically correct and produce identical moments. The visual difference (~0.003 max error) is due to numerical discretization, not incorrect formulation. Legacy Gil-Pelaez method has superior accuracy due to adaptive grid selection.

## Implementation Validation

### Monopore Model Test Case

**Parameters:**
- np = 50 (mean number of pore visits)
- τp = 2.0 s (mean residence time per visit)
- Expected: Mean = 100 s, Variance = 200 s²

**Results:**

| Method | Mean | Variance | Visual Agreement |
|--------|------|----------|------------------|
| GEC Bessel (theory) | 100.00 | 200.00 | Reference |
| Robust GEC | 100.00 | 200.00 | Perfect |
| Simple FFT (this work) | 100.00 | 200.00 | Excellent (error 0.003) |
| Gil-Pelaez (legacy) | 100.00 | 200.00 | Perfect (error ~0) |

### Three Equivalent Methods

Implemented in `study/monopore_study_retry.ipynb`:

1. **GEC Bessel formula** (Giddings 1955):
   ```python
   f(t) = √(np/(t·τp)) · e^(-t/τp - np) · I₁(√(4np·t/τp))
   ```

2. **Robust GEC** (removes singularity at t=0):
   ```python
   def gec_monopore_pdf_robust(t, np_, tp_):
       u = 2 * np.sqrt(np_ * t / tp_)
       return (1/(2*tp_)) * np.exp(-t/tp_ - np_) * (np.exp(u) - np.exp(-u))
   ```

3. **CF + FFT numerical inversion**:
   ```python
   gec_monopore_cf = lambda s, np_, tp_: np.exp(np_ * (1/(1 - 1j * tp_ * s) - 1))
   pdf = FftInvPdf(gec_monopore_cf)  # Legacy implementation
   ```

All three methods produce **identical results** when using correct exponential CF.

## Critical Debugging Steps Resolved

### 1. FFT Sign Convention (Dec 12)
- **Problem:** Negative values in `peak_levy`
- **Cause:** NumPy `ifft` uses exp(-iωt) but CF uses exp(+iωt)
- **Solution:** Use `np.fft.fftfreq()` and proper frequency ordering
- **Note:** This was a red herring; proper conjugation is automatic in IFFT

### 2. Variance Error (Dec 15)
- **Problem:** Variance consistently 100 instead of 200
- **Cause:** Used delta function CF instead of exponential CF
- **Solution:** Changed to `φ_X(ω) = λ/(λ - iω)` for individual events
- **Result:** Perfect moment agreement

### 3. Moment Calculation (Dec 15)
- **Problem:** Moments computed on interpolated grid
- **Cause:** `np.trapezoid(t * pdf_interp, t)` used sparse output grid
- **Solution:** Compute on full FFT grid before interpolation
- **Result:** Accurate variance calculation

### 4. Normalization Order (Dec 15)
- **Problem:** `np.maximum(peak, 0)` after normalization changed integral
- **Solution:** Clip negative values **before** normalizing
- **Result:** Proper unit area normalization

## Recommended Implementation

### For Production Use

**Use legacy FftInvPdf** for maximum accuracy:
```python
from molass_legacy.SecTheory.SecPDF import FftInvPdf

# Define CF with exponential distribution
gec_monopore_cf = lambda s, np_, tp_: np.exp(np_ * (1/(1 - 1j * tp_ * s) - 1))

# Create PDF function
pdf = FftInvPdf(gec_monopore_cf)

# Evaluate
result = pdf(t_values, np_=50, tp_=2.0)
```

**Advantages:**
- Gil-Pelaez adaptive grid (Witkovský 2018)
- Machine-precision accuracy
- Automatic domain selection
- Well-tested in molass ecosystem

### For Validation/Development

**Simple FFT is acceptable:**
```python
def simple_fft_inversion(t, np_, tp_, n_points=8192):
    # ... (see Method 1 above)
```

**Advantages:**
- Transparent implementation
- Easy to understand and modify
- Sufficient accuracy for validation (error ~0.003)
- Correct moments (error ~0.0001)

## Implications for SEC-SAXS Modeling

### 1. Multi-Site Sorption Models

**Nonspecific (NS) + Specific (S) sites:**
```python
# Parameters
r_NS = 1000   # Events at NS sites
r_S = 10      # Events at S sites
tau_NS = 0.068  # Mean NS residence time
tau_S = 1.6     # Mean S residence time

# Characteristic function
lambda_NS = 1.0 / tau_NS
lambda_S = 1.0 / tau_S
phi_NS = lambda_NS / (lambda_NS - 1j * omega)
phi_S = lambda_S / (lambda_S - 1j * omega)

cf = np.exp(r_NS * (phi_NS - 1) + r_S * (phi_S - 1))
```

### 2. Continuous Distributions (Sepsey 2014)

**Lognormal pore size distribution:**
```python
# Pore radius distribution
r_pores = np.linspace(r_min, r_max, n_bins)
g_r = lognormal_pdf(r_pores, mu_ln, sigma_ln)

# Residence time as function of pore size
tau_pores = residence_time_model(r_pores, D, L)

# Integrate over distribution
sum_term = 0
for tau, g, dr in zip(tau_pores, g_r, np.diff(r_pores)):
    lambda_exp = 1.0 / tau
    phi_X = lambda_exp / (lambda_exp - 1j * omega)
    sum_term += (phi_X - 1) * g * dr

cf = np.exp(rM_bar * sum_term)
```

### 3. Connection to Current SDM

**Current approach** (`molass/SEC/Models/SDM.py`):
- Empirical moment matching
- Parameters: N, T, N0, t0, poresize exponents
- Fits mean/variance to data

**Proposed Lévy approach:**
- Extract sorption time distributions from data
- Physical interpretation of {τS,i, ΔF(τS,i)}
- Natural handling of multi-population systems
- Better extrapolation to unseen conditions

## Files Modified/Created

### Session Dec 12
- `study/src/levy_vs_montecarlo_demo.py` - FFT debugging
- `study/src/pasti2005_levy_inversion.py` - DiI dye NS+S demo
- `study/pasti2005_case_A_rM_comparison.png`
- `study/pasti2005_case_B_peak.png`

### Session Dec 15-16
- `study/monopore_study.ipynb` - Variance debugging
- `study/monopore_study_retry.ipynb` - Clean validation
- `study/witkovsky_2018_extracted.txt` - Gil-Pelaez documentation
- Documentation cells added to notebooks

## Key Code Snippets

### Correct Exponential CF

```python
def gec_monopore_cf(omega, np_, tp_):
    """
    Characteristic function for monopore SEC.
    Uses EXPONENTIAL distribution for individual pore visits.
    """
    lambda_exp = 1.0 / tp_
    phi_X = lambda_exp / (lambda_exp - 1j * omega)  # CF of Exp(λ)
    return np.exp(np_ * (phi_X - 1))
```

### Moment Verification

```python
# Compute on FULL FFT grid (not interpolated output)
time_full, pdf_full = levy_pdf(t, np_, tp_, return_full_grid=True)
dt = time_full[1] - time_full[0]

mean = np.sum(time_full * pdf_full * dt)
variance = np.sum((time_full - mean)**2 * pdf_full * dt)

# Theory
mean_theory = np_ * tp_
variance_theory = 2 * np_ * tp_**2

print(f"Mean: {mean:.4f} (theory: {mean_theory:.4f})")
print(f"Variance: {variance:.4f} (theory: {variance_theory:.4f})")
```

### FFT Configuration

```python
# Recommended settings
n_points = 8192              # High resolution
dt = expected_mean / n_points * 4  # Time spacing
omega = np.fft.fftfreq(n_points, dt) * 2 * np.pi
```

## Summary of Key Insights

1. **Exponential vs Delta CF:**
   - Giddings theory assumes **exponential** residence times, not fixed durations
   - Exponential CF: variance = 2np·τp²
   - Delta CF: variance = np·τp² (wrong by factor of 2)

2. **Compound Poisson Variance:**
   - Var[total] = λ × E[X²], not λ × Var[X]
   - For exponential: E[X²] = 2τp², giving correct variance

3. **FFT Method Comparison:**
   - Simple FFT (fixed grid): error ~0.003, easy to understand
   - Gil-Pelaez (adaptive grid): error ~0, production-ready
   - Both are correct; difference is only numerical accuracy
   - **Use legacy FftInvPdf for production work**

4. **Numerical Best Practices:**
   - Clip negative values **before** normalizing
   - Compute moments on full FFT grid, not interpolated output
   - Use sufficient resolution (n_points ≥ 8192)
   - Verify moments match theory before trusting visual agreement

5. **Legacy Code Justification:**
   - `molass_legacy.SecTheory.SecPDF.FftInvPdf` implements Witkovský 2018 Gil-Pelaez formula
   - Adaptive six-sigma grid selection for optimal accuracy
   - Trapezoidal quadrature with proper weights
   - **Should be retained and used for all production calculations**

## Next Steps

1. ✅ Exponential CF validated for monopore model
2. ✅ Simple FFT vs Gil-Pelaez comparison completed
3. ✅ Legacy code theoretical foundation understood
4. ⏭️ Implement multi-site model (NS + S sites) with correct exponential CF
5. ⏭️ Test continuous distribution integration (Sepsey 2014)
6. ⏭️ Design CF-based fitting procedure for SEC-SAXS data
7. ⏭️ Re-implement SDM using Lévy framework
8. ⏭️ Validate on real `decomposition.xr_ccurves` data

## References

1. Giddings, J.C., Eyring, H., Carmichael, L.T. (1955). "Stochastic Theory of Chromatography"
2. Dondi, F., et al. (2002). "Classification of GEC Models"
3. Pasti, F., et al. (2005). "Lévy Process Framework for Single-Molecule Chromatography"
4. Sepsey, A., et al. (2014). "Pore Size Distribution Effects in SEC"
5. Witkovský, V. (2018). "Computing the Distribution of a Linear Combination of Inverted Gamma Variables" - Gil-Pelaez inversion formula

---

**Status:** Theoretical foundation complete. Ready for production implementation in molass SDM framework.
