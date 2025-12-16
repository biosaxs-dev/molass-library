# Session Summary: Understanding "Lévy Awareness" in SDM Implementation

**Date**: December 16, 2025  
**Topic**: What does "Lévy-aware" mean for practical CF-based SDM implementation?

---

## Core Question

> "I want to reexamine and possibly rewrite or extend my implementation of 'stochastic dispersive model' in a **Lévy approach aware manner**"

**Key insight from session:** Being "Lévy-aware" means **invoking Lévy-Khintchine and Lévy-Itô theorems as mathematical shortcuts**, not just using a CF formula.

---

## The Fundamental Distinction

### Two Ways to Arrive at the Same CF:

**Approach A: Lévy-Theorem-First (Pasti 2005 style)**
1. Recognize process has independent, stationary increments → It's a Lévy process
2. **Invoke Lévy-Khintchine theorem:** CF must have form φ(ω,t) = exp[t·ψ(ω)]
3. **Apply Lévy-Itô decomposition:** X = Brownian + drift + jumps (independent)
4. **Use proven formulas directly** without re-deriving

**Approach B: Chromatographic First Principles**
1. Start from single-molecule trajectories
2. Derive ensemble average from statistics
3. Build up CF from convolutions and transformations
4. Observe result happens to be a Lévy process (not used as starting point)

**Pasti 2005 uses Approach A** - they explicitly cite Lévy-Khintchine as the foundation.

---

## Wikipedia Definition: What IS a Lévy Process?

From https://en.wikipedia.org/wiki/Lévy_process:

### Four Defining Properties:
1. **X₀ = 0** almost surely
2. **Independent increments**: Non-overlapping intervals are independent
3. **Stationary increments**: Distribution depends only on interval length
4. **Continuity in probability**: No jumps larger than ε as h→0

### Two Key Theorems:

**Lévy-Khintchine Representation:**
```
φ(ω,t) = exp[t(iγω - σ²ω²/2 + ∫[e^(iωx) - 1 - iωx·𝟙_{|x|<1}]ν(dx))]
```
- **Uniquely determined by triplet (γ, σ², ν)**
- γ = drift, σ² = Brownian variance, ν = Lévy measure (jump distribution)

**Lévy-Itô Decomposition:**
```
X(t) = σB(t) + γt + Y(t) + Z(t)
       ───────  ──   ─────  ─────
       Brownian Drift Large  Small
                      jumps  jumps
```
- **Components are INDEPENDENT**
- Variances add: Var[X] = Var[B] + Var[Y] + Var[Z]
- CFs multiply: φ_X = φ_B · φ_drift · φ_Y · φ_Z

---

## What "Lévy Awareness" Adds to CF-Only Implementation

### Six Practical Insights (NO Monte Carlo needed):

| # | Insight | Theorem | Practical Benefit |
|---|---------|---------|-------------------|
| 1 | **Infinite divisibility** | Lévy-Khintchine | Validate CF before expensive FFT |
| 2 | **Analytical moments** | Cumulant theorem | Fast diagnostics: E[X] = γ + λ∫τν(dτ) |
| 3 | **Modular composition** | Lévy-Itô independence | Natural multi-mechanism parameterization |
| 4 | **Tail behavior** | Lévy measure properties | Predict asymptotic decay, regularization |
| 5 | **Numerical stability** | Compositional structure | Avoid log(CF) when CF→0, use exp(Σ terms) |
| 6 | **Parameter identifiability** | Lévy measure structure | Fix degeneracies in optimization |

**Key point:** These are **implementation recipes**, not just theoretical properties!

---

## Code Example: What Makes it "Lévy-Aware"?

### The `LevyAwareSDM` Class Breakdown

```python
class LevyAwareSDM:
    def moments(self):
        mean = var = 0
        for name, n, taus, probs in self.mechanisms:
            tau_mean = np.dot(taus, probs)
            tau_2nd_moment = np.dot(taus**2, probs)
            mean += n * tau_mean        # ← THEOREM: E[X] = γ + λ·E[τ]
            var += n * tau_2nd_moment   # ← THEOREM: Var[X] = σ² + λ·E[τ²]
```

**Lévy-aware because:**
- Doesn't derive these formulas from chromatography
- **Directly applies** Lévy-Khintchine theorem for compound Poisson
- Trusts theorem-proven formula: ∫τ^k ν(dτ) = Σ pᵢ·τᵢ^k

```python
    def log_cf(self, omega):
        log_phi = 0
        for name, n, taus, probs in self.mechanisms:
            for tau, p in zip(taus, probs):
                log_phi += n * p * (np.exp(1j * omega * tau) - 1)
```

**Lévy-aware because:**
- Structure is **exactly** Lévy-Khintchine: λ∫[e^(iωτ) - 1]ν(dτ)
- The `(e^(iωτ) - 1)` is **from the theorem**, not derived
- The `-1` is the **Lévy-Khintchine compensator** (ensures X₀=0)

```python
    def log_cf(self, omega):
        log_phi = 0
        for name, n, taus, probs in self.mechanisms:
            log_phi += ...  # Each mechanism ADDS
```

**Lévy-aware because:**
- **Lévy-Itô theorem:** Independent processes add in log space
- Loop structure **directly implements theorem**
- No need to prove independence - theorem guarantees it!

```python
    def _validate_parameters(self):
        assert n >= 0
        assert np.all(taus > 0)
        assert np.isclose(sum(probs), 1.0)
```

**Lévy-aware because:**
- These are **theorem requirements** for infinite divisibility
- Not just "good practice" - prerequisites for valid Lévy process!

```python
    def objective_function(self, data):
        # First check: moment matching (FAST)
        mean_model, var_model = self.moments()  # No FFT!
        
        if moment_error > threshold:
            return large_penalty  # Skip expensive PDF
        
        # Otherwise compute full PDF (SLOW)
        pdf_model = self.pdf(t_grid)
```

**Lévy-aware because:**
- Exploits **analytical moments** from Lévy measure
- Theorem-based speedup: screen 1000 candidates fast, only compute PDF for promising ones
- Without Lévy awareness: compute PDF every time (1000× slower)

---

## Refactoring: felinger1999_stochastic_dispersive.py

### New Theorem-First Methods Added:

#### 1. **`levy_triplet` Property**
```python
@property
def levy_triplet(self) -> dict:
    """By Lévy-Khintchine theorem, (γ, σ², ν) uniquely determines process."""
    return {
        'gamma': self.column.t0,
        'sigma_squared': 2 * self.column.D * self.column.t0 / self.column.u,
        'lambda_rate': self.n_ads,
        'levy_measure': self.sorption
    }
```

#### 2. **`validate_infinite_divisibility()`**
```python
def validate_infinite_divisibility(self, n_test=10):
    """Check φ(ω) = [φ(ω/n)]ⁿ (Lévy requirement)."""
    # Tests theorem requirement
```

#### 3. **`variance()` - REFACTORED**
```python
def variance(self) -> dict:
    """Variance by Lévy-Itô decomposition theorem.
    
    By theorem: X = X₁ + X₂ + X₃ (independent)
    Therefore: Var[X] = Var[X₁] + Var[X₂] + Var[X₃]
    
    No derivation needed - trust the theorem!
    """
    triplet = self.levy_triplet
    
    var_drift = 0  # Deterministic
    var_brownian = triplet['sigma_squared'] * (1 + k_prime)**2
    var_poisson = triplet['lambda_rate'] * self.sorption.variance()
    
    return {
        'total': var_drift + var_brownian + var_poisson,  # Theorem!
        'drift': var_drift,
        'brownian': var_brownian,
        'poisson': var_poisson
    }
```

#### 4. **`variance_legacy()` - For Comparison**
```python
def variance_legacy(self):
    """Original manual calculation.
    Result MUST match variance() - theorem guarantees it!
    """
    # Old chromatographic derivation
```

#### 5. **`characteristic_function()` - REFACTORED**
```python
def characteristic_function(self, omega):
    """Direct application of Lévy-Khintchine formula.
    
    log Φ(ω) = iγω - σ²ω²/2 + λ∫[e^(iωτ) - 1]ν(dτ)
    
    We don't derive this - Lévy-Khintchine PROVES it!
    """
    triplet = self.levy_triplet
    
    log_phi = (
        1j * omega * triplet['gamma']  # Drift
        - triplet['sigma_squared'] * omega**2 / 2  # Brownian
        + triplet['lambda_rate'] * (cf_s - 1)  # Poisson
    )
    
    return np.exp(log_phi)
```

#### 6. **`moments_from_levy_measure()`**
```python
def moments_from_levy_measure(self):
    """Compute mean/variance WITHOUT FFT.
    
    Theorem: E[X] = γ + λ·E[τ], Var[X] = σ² + λ·Var[τ]
    
    This is EXACT - no simulation needed!
    """
    # Direct from (γ, σ², ν) using theorem
```

#### 7. **`demo_levy_theorem_validation()`**
```python
def demo_levy_theorem_validation():
    """Demonstrate all theorem-based calculations."""
    # Shows:
    # - Lévy triplet extraction
    # - Infinite divisibility check
    # - Variance: theorem vs legacy (match!)
    # - Component decomposition
    # - CF equivalence (Khintchine vs Itô)
```

---

## Key Philosophical Shift

### BEFORE (Non-Lévy-Aware):
```python
def sdm_variance(npi, tpi, N0, t0):
    # Derive from chromatography principles
    variance_kinetic = npi * 2 * tpi**2  # Derived
    k_prime = npi * tpi / t0
    variance_brownian = 1/(2*N0) * t0 * (1 + k_prime)**2  # Derived
    
    # Prove independence to add
    total = variance_kinetic + variance_brownian
```

**Problems:**
- ❌ Must derive every formula
- ❌ Must prove independence
- ❌ No validation of result
- ❌ Hard to extend

### AFTER (Lévy-Aware):
```python
def sdm_variance_levy_aware(npi, tpi, N0, t0):
    # Extract Lévy triplet
    gamma = t0
    sigma_squared = 1/(2*N0) * t0
    lambda_rate = npi
    levy_measure_variance = 2 * tpi**2
    
    k_prime = npi * tpi / t0
    
    # Apply Lévy-Itô theorem: variances ADD
    return (
        0 +  # Drift (deterministic)
        sigma_squared * (1 + k_prime)**2 +  # Brownian
        lambda_rate * levy_measure_variance  # Poisson
    )  # Theorem guarantees this!
```

**Advantages:**
- ✅ No derivation - trust theorem
- ✅ Validation built-in
- ✅ Clear component structure
- ✅ Easy to extend (add Lévy component → variance adds automatically)

---

## Summary: What "Lévy-Aware" Really Means

### It's NOT:
- ❌ Just using a CF formula
- ❌ Mentioning "Lévy process" in comments
- ❌ Using FFT for peak calculation

### It IS:
- ✅ **Recognizing** you're implementing a Lévy process
- ✅ **Invoking theorems** as shortcuts (Lévy-Khintchine, Lévy-Itô)
- ✅ **Trusting** proven formulas instead of re-deriving
- ✅ **Exploiting** structure (modular composition, analytical moments)
- ✅ **Validating** using theorem requirements (infinite divisibility)

### Concrete Benefits for Optimization:

1. **Fast parameter screening** - Use analytical moments before expensive FFT
2. **Modular design** - Add/remove mechanisms independently
3. **Built-in validation** - Theorem constraints catch invalid parameters
4. **Clear structure** - (γ, σ², ν) triplet makes debugging easier
5. **Guaranteed correctness** - If triplet is valid, process is valid

---

## Files Modified/Created

### Modified:
- **`study/src/felinger1999_stochastic_dispersive.py`**
  - Added `levy_triplet` property
  - Added `validate_infinite_divisibility()`
  - Refactored `variance()` to use Lévy-Itô directly
  - Added `variance_legacy()` for comparison
  - Refactored `characteristic_function()` to show Lévy-Khintchine structure
  - Added `moments_from_levy_measure()`
  - Added `demo_levy_theorem_validation()`

### Created:
- **`study/levy-vs-montecarlo.ipynb`** (extended)
  - Added 6 practical Lévy insights for CF-only implementation
  - Added detailed annotation of `LevyAwareSDM` class
  - Added comparison: Lévy-aware vs non-Lévy-aware approaches

---

## Next Steps for Your SDM Implementation

### 1. Apply Lévy-Aware Refactoring to Current SDM:
```python
# Current: molass_legacy.Models.Stochastic.DispersivePdf.dispersive_monopore_pdf

# Refactor to:
class LevyAwareSDM:
    @property
    def levy_triplet(self):
        return {
            'gamma': self.t0,
            'sigma_squared': 1/(2*self.N0) * self.t0,
            'lambda': self.npi,
            'levy_measure': ExponentialMeasure(self.tpi)
        }
    
    def variance_by_theorem(self):
        # Direct from Lévy-Itô - no derivation
        triplet = self.levy_triplet
        k_prime = triplet['lambda'] * self.tpi / triplet['gamma']
        return (
            0 +  # Drift
            triplet['sigma_squared'] * (1 + k_prime)**2 +  # Brownian
            triplet['lambda'] * (2 * self.tpi**2)  # Poisson
        )
```

### 2. Extend to Multi-Site (Pasti 2005 NS+S Model):
```python
class MultiSiteLevySDM(LevyAwareSDM):
    def __init__(self, sites):
        """sites: [(n_i, tau_i)] for each site type"""
        self.sites = sites
    
    @property
    def levy_measure(self):
        """Discrete Lévy measure: ν = Σ pᵢδ(τᵢ)"""
        return DiscreteMeasure(self.sites)
    
    def moments_from_measure(self):
        # By theorem: E[X] = Σ nᵢ·τᵢ, Var[X] = Σ nᵢ·2τᵢ²
        mean = sum(n * tau for n, tau in self.sites)
        var = sum(n * 2 * tau**2 for n, tau in self.sites)
        return mean, var
```

### 3. Add Moment-Based Optimization Screening:
```python
def optimize_sdm(data, initial_params):
    """Two-tier optimization using Lévy awareness."""
    
    def cheap_objective(params):
        """Fast screening using analytical moments."""
        model = LevyAwareSDM(params)
        mean_model, var_model = model.moments_from_measure()  # No FFT!
        mean_data, var_data = np.mean(data), np.var(data)
        return (mean_model - mean_data)**2 + (var_model - var_data)**2
    
    # Stage 1: Coarse search using moments (FAST)
    candidates = grid_search(cheap_objective, initial_params)
    
    # Stage 2: Refine using full PDF (SLOW)
    def expensive_objective(params):
        model = LevyAwareSDM(params)
        pdf_model = model.pdf_via_fft(t_grid)  # Expensive
        return chi_squared(pdf_model, data)
    
    best = refine_search(expensive_objective, candidates[:10])
    return best
```

---

## Key References

- **Lévy Process (Wikipedia)**: https://en.wikipedia.org/wiki/Lévy_process
- **Felinger et al. 1999**: Anal. Chem. 71(20), 4472-4479
- **Pasti et al. 2005**: Anal. Chem. 77(8), 2524-2535
- **Your LEARNING_SUMMARY.md**: Comprehensive Lévy framework overview

---

## Remember

**"Lévy-aware" = Invoke theorems as shortcuts, not just formulas**

The theorems (Lévy-Khintchine, Lévy-Itô) provide:
1. Guaranteed correctness
2. Computational efficiency (analytical moments)
3. Clear structure (modular composition)
4. Built-in validation (infinite divisibility)

This is what Pasti 2005 brought to chromatography - recognizing the Lévy structure and **exploiting it**!

---

*End of Session Summary*
