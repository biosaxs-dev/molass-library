# Session Summary: Fixing Lévy FFT Variance Issue (Dec 15, 2024)

## Problem Statement

When implementing the Lévy characteristic function approach for monopore SEC peaks, we encountered a persistent issue:
- ✅ Mean was correct (100s)
- ❌ Variance was consistently **half** of the theoretical value (100 instead of 200)
- ❌ Visual residuals were large (max ~0.42-0.69)

## Investigation Process

### 1. Initial Debugging Attempts

**Normalization Issues:**
- Found that `np.maximum(peak, 0)` clipping negative values **after** normalization changed the sum
- **Fix:** Clip before normalizing: `peak = np.maximum(peak, 0)` → then `peak = peak / (np.sum(peak) * dt)`
- Result: Integral now correct (1.0), but variance still wrong

**Moment Calculation Issues:**
- Discovered moments were computed on interpolated grid instead of full FFT grid
- **Fix:** Compute moments on full FFT output before interpolation
- Result: Mean correct (100.00), but variance still 100 instead of 200

### 2. Legacy Code Comparison

Examined `molass_legacy.SecTheory.SecPDF.FftInvPdf` which uses different FFT normalization:
- Custom scaling factors `C` and `D` for phase correction
- Symmetrization of CF before FFT
- **Result:** Better visual agreement (max error 0.012 vs 0.42), but **same variance issue** (100 instead of 200)

**Key insight:** The variance problem is fundamental to the CF formulation, not the FFT implementation!

### 3. Root Cause Analysis

**The Critical Mistake:**

We were using the wrong characteristic function!

```python
# WRONG: Delta function CF (deterministic sorption time)
φ(ω) = exp[np × (exp(iω·τp) - 1)]
```

This assumes each sorption event has **deterministic duration** τp (delta function).

**Variance from this CF:**
- Taylor expansion: φ(ω) ≈ exp[iω·np·τp - ω²·np·τp²/2]
- This gives variance = np·τp² = **100** (half of correct value!)

**The Giddings Model Reality:**

The Giddings-Eyring-Carmichael (1955) theory assumes each pore visit has **exponentially distributed** duration with mean τp, not fixed duration!

```python
# CORRECT: Exponential distribution CF
λ = 1/τp
φ_X(ω) = λ / (λ - iω) = (1/τp) / (1/τp - iω)
φ(ω) = exp[np × (φ_X(ω) - 1)]
```

**Variance from exponential distribution:**
- For exponential: E[X] = τp, Var[X] = τp², E[X²] = 2τp²
- Compound Poisson: Var[total] = np × E[X²] = np × 2τp² = **200** ✓

## Solution

### Correct Implementation

```python
def levy_monopore_pdf_exponential(t, np_, tp_, n_points=8192, return_full_grid=False):
    """
    Monopore PDF using Lévy CF with EXPONENTIAL distribution for individual events.
    This gives the correct variance = 2·np·τp².
    """
    # Estimate time scale for grid
    expected_mean = np_ * tp_
    dt = expected_mean / n_points * 4
    
    # Build frequency array
    omega = np.fft.fftfreq(n_points, dt) * 2 * np.pi
    
    # Characteristic function with EXPONENTIAL individual events
    lambda_exp = 1.0 / tp_
    phi_X = lambda_exp / (lambda_exp - 1j * omega)  # CF of exponential(τp)
    cf = np.exp(np_ * (phi_X - 1))
    
    # IFFT to get PDF
    peak = np.fft.ifft(cf).real
    peak = np.fft.ifftshift(peak)
    
    # Ensure non-negative BEFORE normalizing (clipping changes the sum!)
    peak = np.maximum(peak, 0)
    
    # Normalize to unit area AFTER clipping
    peak = peak / (np.sum(peak) * dt)
    
    # Time grid
    time_grid = np.arange(n_points) * dt
    
    if return_full_grid:
        return time_grid, peak
    else:
        pdf = np.interp(t, time_grid, peak, left=0, right=0)
        return pdf
```

### Results

**With exponential CF:**
- Mean: 100.0000 ✓
- Variance: 200.0002 ✓ (vs theoretical 200)
- Max error vs GEC Bessel: 0.0027 ✓ (excellent!)
- Visual agreement: Nearly perfect overlay

**Comparison table:**

| Method | Mean | Std Dev | Variance | Max Error |
|--------|------|---------|----------|-----------|
| GEC (Bessel) | 100.00 | 14.14 | 200.00 | - |
| Lévy (delta CF) | 100.00 | 10.02 | 100.48 | 0.42 |
| Lévy (exponential CF) | 100.00 | 14.14 | 200.00 | 0.0027 |
| Theory | 100.00 | 14.14 | 200.00 | - |

## Key Insights

### 1. **Compound Poisson Process Variance Formula**

For a compound Poisson process with rate λ and event size distribution X:
```
Var[total] = λ × E[X²]
NOT λ × Var[X]
```

For exponential with mean τp:
- E[X²] = Var[X] + E[X]² = τp² + τp² = 2τp²
- Therefore: Var[total] = np × 2τp²

### 2. **Physical Interpretation**

The Giddings stochastic theory models:
- **Number of events:** Poisson distributed with mean np
- **Duration of each event:** Exponentially distributed with mean τp
- **Total time:** Sum of random number of random durations

This is a **compound Poisson process**, not a simple Poisson process!

### 3. **Connection to Bessel Function Formula**

The GEC formula with modified Bessel function I₁:
```
f(t) = √(np/(t·τp)) · e^(-t/τp - np) · I₁(√(4np·t/τp))
```

This **exactly** represents the compound Poisson process with exponential event times. The Lévy CF approach with exponential distribution reproduces this!

## Implications for SEC-SAXS Work

### For Multi-Site Models (NS + S)

**Correct formulation:**
```python
# Each site type has its own exponential distribution
lambda_NS = 1.0 / tau_NS
lambda_S = 1.0 / tau_S

phi_NS = lambda_NS / (lambda_NS - 1j * omega)
phi_S = lambda_S / (lambda_S - 1j * omega)

# Compound CF
cf = np.exp(r_NS * (phi_NS - 1) + r_S * (phi_S - 1))
```

NOT:
```python
# WRONG - uses delta functions
cf = np.exp(r_NS * (np.exp(1j*omega*tau_NS) - 1) + 
            r_S * (np.exp(1j*omega*tau_S) - 1))
```

### For Continuous Distributions

When integrating over pore size distribution:
```python
# For each pore size with residence time τ(r) and fraction ΔF(r)
for tau, deltaF in zip(tau_values, deltaF_values):
    lambda_exp = 1.0 / tau
    phi_X = lambda_exp / (lambda_exp - 1j * omega)
    sum_term += (phi_X - 1) * deltaF

cf = np.exp(rM_bar * sum_term)
```

## Files Modified

- `study/monopore_study.ipynb`: Added investigation cells and correct implementation
- New cells added:
  - Variance issue investigation (delta vs exponential CF)
  - Legacy FFT comparison using `molass_legacy.SecTheory.SecPDF`
  - Correct implementation with exponential CF
  - Comprehensive moment comparison

## References

1. **Giddings, Eyring, Carmichael (1955):** Original stochastic theory - assumes exponential event times
2. **Pasti et al. (2005):** Lévy process characteristic function approach
3. **Dondi et al. (2002):** Multi-site sorption kinetics
4. **Legacy code:** `molass_legacy.SecTheory.SecPDF` - working FFT implementation

## Next Steps

1. ✅ Update `levy_vs_montecarlo_demo.py` with exponential CF
2. ✅ Implement multi-site model with correct exponential distributions
3. ✅ Test with lognormal pore size distributions (Sepsey 2014)
4. Document the theoretical basis for exponential vs delta CF choice
5. Integrate into main molass SDM implementation

## Code Snippets for Reference

### Delta vs Exponential CF Comparison

```python
# Delta function (WRONG for Giddings model)
def levy_cf_delta(omega, np_, tp_):
    return np.exp(np_ * (np.exp(1j * omega * tp_) - 1))

# Exponential distribution (CORRECT for Giddings model)
def levy_cf_exponential(omega, np_, tp_):
    lambda_exp = 1.0 / tp_
    phi_X = lambda_exp / (lambda_exp - 1j * omega)
    return np.exp(np_ * (phi_X - 1))
```

### Moment Calculation (Critical!)

```python
# WRONG: Moments on interpolated grid
mean_wrong = np.trapezoid(t * pdf_interp, t)  # t is sparse

# CORRECT: Moments on full FFT grid
time_full, pdf_full = levy_pdf(t, np_, tp_, return_full_grid=True)
dt = time_full[1] - time_full[0]
mean_correct = np.sum(time_full * pdf_full * dt)
var_correct = np.sum((time_full - mean_correct)**2 * pdf_full * dt)
```

## Conclusion

The factor-of-2 variance error was caused by using a **delta function** for individual sorption times instead of the correct **exponential distribution** assumed by the Giddings stochastic theory. Once corrected, the Lévy characteristic function approach perfectly reproduces the GEC Bessel function formula with:
- Exact mean (100.00)
- Exact variance (200.00)
- Excellent visual agreement (max error 0.0027)

This validates the Lévy framework as the correct computational approach for SEC stochastic modeling, with the critical requirement to use exponential distributions for individual event times.
