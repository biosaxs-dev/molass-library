# Learning Summary: Chromatography Through the Lévy Lens

**Date**: December 9, 2025  
**Topic**: Understanding stochastic chromatography models via Lévy process theory

---

## Key Insight: The Lévy Process Unification

All stochastic chromatography models (Giddings-Eyring 1955 → Felinger 1999 → Pasti 2005 → Kovalenko 2025) are **special cases of Lévy processes**, even though the original authors didn't always recognize this!

---

## The Three Papers: A Theoretical Hierarchy

### 1. **Felinger et al. 1999** (Anal. Chem. 71, 4472-4479)
*"Stochastic-Dispersive Theory of Chromatography"*

**What they did:**
- Combined stochastic adsorption-desorption with axial dispersion
- Derived characteristic function (CF) for retention time distribution
- Calculated **analytical moments** (mean, variance, skewness, kurtosis)
- Showed plate height H = B/u + C·u (van Deemter equation)
- Analyzed heterogeneous surfaces (two-site model, log-normal energy distributions)

**Key equation (eq 13):**
```
Φ(ω) = exp[iωt₀ - Dt₀ω²/(2u) + n·(Φ_s(ω) - 1)]
```

**What they DIDN'T know:**
- This is a Lévy process in canonical form!
- Connection to single-molecule experiments
- General Lévy-Khintchine framework

---

### 2. **Pasti et al. 2005** (Anal. Chem. 77, 2524-2535)
*"Unifying Chromatographic and Single-Molecule Observations via Lévy Processes"*

**What they did:**
- Recognized that eq 13 is the **Lévy-Khintchine canonical form**
- Connected ensemble chromatography to single-molecule fluorescence
- Implemented FFT inversion for peak calculation (Mathematica code in Figure 2)
- Showed Lévy measure ν(dτ) = sorption time distribution f_s(τ)

**Key insight:**
```
log Φ(ω) = iγω - σ²ω²/2 + λ∫[e^(iωτ) - 1]ν(dτ)
           ────   ─────────  ────────────────────
           DRIFT  BROWNIAN   COMPOUND POISSON
```

This is **always** a Lévy process, regardless of the sorption model!

---

### 3. **Kovalenko & Landes 2025** (J. Phys. Chem. C)
*"Rare Site Clustering and Peak Broadening"*

**What they added:**
- **Spatial effects**: Clustering of rare sites (cluster_size parameter)
- **Intermediate phase**: Diffusion layer between mobile and stationary phases
- **Monte Carlo validation**: Showed spatial clustering breaks Felinger's homogeneity assumption
- Demonstrated that cluster_size=16 causes significant extra broadening

**Key finding:**
- When rare sites are clustered, molecules get "trapped" in slow regions
- This violates the independence assumption in Felinger/Pasti models
- **Monte Carlo is necessary** to capture spatial heterogeneity

---

## The Lévy Process Framework: What Is It?

### Canonical Decomposition (Lévy-Itô)

Every Lévy process is a sum of **three independent components**:

1. **Drift**: γ·t (deterministic linear motion)
2. **Brownian**: σ·B(t) (Gaussian random walk)
3. **Jump**: Compound Poisson process with rate λ and jump distribution ν

For chromatography:
- γ = t₀ = L/u (hold-up time)
- σ² = 2DL/u² (dispersion variance)
- λ = n (number of adsorption events)
- ν(dτ) = f_s(τ)dτ (sorption time distribution)

### Different Sorption Models = Different Lévy Processes

| Sorption Model | f_s(τ) | Lévy Process Type | Activity |
|----------------|--------|-------------------|----------|
| **Homogeneous** (exponential) | (1/τ̄)e^(-τ/τ̄) | **Gamma process** | Finite |
| **Two-site** (fast + slow) | p·f₁ + (1-p)·f₂ | **Mixed Gamma** | Finite |
| **Log-normal** | Log-normal PDF | **Log-normal subordinator** | Infinite |
| **Discrete** (histogram) | Σ pᵢδ(τ-τᵢ) | **Compound Poisson** | Finite |

---

## Critical Distinction: Analytical vs Numerical

### ✅ ANALYTICAL (Always Possible)

**What:** Moments (mean, variance, skewness, kurtosis), plate properties (N, H, u_opt)

**How:** Derivatives of cumulant generating function K(ω) = log Φ(iω) at ω=0

**Why it works:**
```
κ₁ = K'(0) = mean
κ₂ = K''(0) = variance
κ₃ = K'''(0) = skewness numerator
κ₄ = K''''(0) = kurtosis numerator
```

**Examples (Felinger 1999 eqs 32-42):**
- Retention time: t_R = t₀(1 + k')
- Variance: Var = 2Dt₀(1+k')²/u + n(m₂-m₁²)
- Plate number: 1/N = 2D/(uL) + (m₂-m₁²)/(nm₁²)

### ⚠️ NUMERICAL (Usually Required)

**What:** Full peak shape f(t) (the actual chromatogram)

**How:** FFT inversion of characteristic function Φ(ω)

**When analytical f(t) exists:**
- Giddings-Eyring-Carmichael (1952): No dispersion → Gamma PDF
- Pure Gaussian: No adsorption → Normal PDF
- **That's it!** (see Dondi 2002)

**When FFT required:**
- Heterogeneous surfaces (two-site, log-normal)
- Stochastic + dispersion combined
- Most realistic chromatography models

**Key point:** You can characterize peak quality (N, H, skewness) **without computing f(t)**!

---

## Why Lévy Framework Matters

### 1. **Unification**
- Single mathematical framework for all chromatography models
- Connects ensemble measurements to single-molecule experiments
- Same formalism from 1952 to 2025

### 2. **Independence**
- Drift, Brownian, and jumps evolve independently
- Variances add: Var[total] = Var[Brownian] + Var[Poisson]
- Enables analytical moment calculations

### 3. **Extensibility**
- New sorption model? Just define new Lévy measure ν(dτ)
- Automatically get CF, moments, FFT inversion
- No need to re-derive everything from scratch

### 4. **Physical Insight**
- Lévy measure ν(dτ) = distribution of surface binding times
- Subordinator = monotone increasing time delays (only positive jumps)
- Infinite activity = continuous energy distribution (log-normal)

---

## Implementation: felinger1999_stochastic_dispersive.py

### Architecture

```
ColumnParameters
    ├─ L, u, D (physical properties)
    └─ t₀, N_disp (derived)

SorptionModel (abstract base)
    ├─ moment(r) → m_r (analytical)
    ├─ characteristic_function(ω) → Φ_s(ω)
    └─ pdf(τ) → f_s(τ)

Concrete Sorption Models:
    ├─ HomogeneousSorption (Gamma process)
    ├─ TwoSiteSorption (Mixed Gamma)
    ├─ LogNormalSorption (Infinite activity)
    └─ DiscreteSorption (Arbitrary histogram)

StochasticDispersiveChromatography
    ├─ retention_time() → t_R (analytical)
    ├─ variance() → {total, kinetics, dispersion} (analytical)
    ├─ plate_number() → N (analytical)
    ├─ plate_height() → H, B, C terms (analytical)
    ├─ optimum_velocity() → u_opt, H_min (analytical)
    ├─ skewness() → S (analytical)
    ├─ excess() → Ex (analytical)
    ├─ characteristic_function(ω) → Φ(ω) (exact)
    └─ calculate_peak() → f(t) (numerical FFT)
```

### Key Features

**Lévy components made explicit:**
```python
# Drift (mobile phase convection)
gamma = self.column.t0
shift = np.exp(1j * omega * gamma)

# Brownian (axial dispersion)
sigma_squared = 2 * self.column.D * self.column.t0 / self.column.u
dispersion = np.exp(-sigma_squared * omega**2 / 2)

# Compound Poisson (adsorption)
lambda_rate = self.n_ads
cf_s = self.sorption.characteristic_function(omega)
poisson = np.exp(lambda_rate * (cf_s - 1))

# Independence: multiply components
return shift * dispersion * poisson
```

**Extensible sorption models:**
```python
# Add new model by subclassing
class MyCustomSorption(SorptionModel):
    def moment(self, order):
        # Analytical moment calculation
        
    def characteristic_function(self, omega):
        # CF of jump distribution
```

---

## Computational Tradeoffs

### Lévy FFT Approach (Pasti 2005)
- **Speed**: ~1000-2000× faster than Monte Carlo
- **Assumptions**: Homogeneous surface, no spatial clustering
- **Best for**: Quick predictions, moment calculations, parameter estimation
- **Implementation**: `pasti2005_levy_inversion.py`, `felinger1999_stochastic_dispersive.py`

### Monte Carlo Approach (Kovalenko 2025)
- **Speed**: Slow (O(n_molecules × n_events))
- **Advantages**: Captures spatial clustering, intermediate phase diffusion
- **Best for**: Validating Lévy predictions, studying spatial effects
- **Implementation**: `single_run.py` (Python/MATLAB)

### When to Use Which?
- **Lévy**: Parameter screening, theoretical predictions, moment analysis
- **Monte Carlo**: Rare site clustering (cluster_size > 1), spatial heterogeneity
- **Both**: Validation and comparison

---

## Files Created This Session

1. **`pasti2005_levy_inversion.py`** (earlier session)
   - FFT implementation of Pasti 2005 Mathematica code
   - Examples from Table 1 (λ-DNA, DiI dye)
   
2. **`levy_vs_montecarlo_demo.py`** (earlier session)
   - Demonstrates equivalence of Lévy and Monte Carlo
   - Convergence study (1/√n error)
   
3. **`felinger1999_stochastic_dispersive.py`** (this session)
   - Clean, extensible Felinger 1999 implementation
   - Annotated with Lévy process interpretation
   - Analytical moments + numerical FFT
   - Demo functions for Figures 1-7

---

## Key Equations Reference

### Characteristic Function (Felinger 1999 eq 13)
```
Φ(ω) = exp[iωt₀ - Dt₀ω²/(2u) + n·(Φ_s(ω) - 1)]
```

### Lévy-Khintchine Canonical Form
```
log Φ(ω) = iγω - σ²ω²/2 + λ∫[e^(iωτ) - 1]ν(dτ)
```

### Variance Decomposition
```
Var[total] = 2Dt₀(1+k')²/u + n(m₂ - m₁²)
             ────────────────   ──────────
             Brownian           Poisson
```

### Plate Height (van Deemter)
```
H = B/u + C·u

B = 2D (eddy diffusion)
C = (m₂ - m₁²)L/(nm₁²) (mass transfer)
```

### Optimum Velocity
```
u_opt = √(B/C)
H_min = 2√(BC)
```

---

## What You Now Understand

### Theoretical
✅ Felinger 1999 characteristic function is a Lévy process  
✅ Three independent components: drift, Brownian, compound Poisson  
✅ Sorption time distribution = Lévy measure ν(dτ)  
✅ Different f_s(τ) → different Lévy processes  
✅ Moments always analytical, peak shape usually numerical  
✅ Connection to single-molecule experiments (Pasti 2005)  
✅ Spatial clustering breaks Lévy assumptions (Kovalenko 2025)  

### Practical
✅ How to calculate moments without simulation  
✅ When analytical solutions exist (very rare!)  
✅ How FFT inversion works (Pasti 2005 method)  
✅ Speed vs accuracy tradeoffs (Lévy vs Monte Carlo)  
✅ Extensible Python implementation with clean architecture  
✅ How to add new sorption models (subclass SorptionModel)  

---

## Next Steps (When You Return)

### 1. Validate Implementation
```python
# Run the demos
python felinger1999_stochastic_dispersive.py

# Compare with your Monte Carlo results
# Check if cluster_size=1 matches Felinger predictions
```

### 2. Explore Spatial Effects
- Compare Felinger (homogeneous) vs Monte Carlo (cluster_size=16)
- Quantify how much clustering increases variance
- Use analytical moments as baseline

### 3. Deep Dive into Kovalenko 2025
- Study intermediate phase model
- Understand when spatial effects dominate
- Connect to experimental observations

### 4. Extend the Framework
- Add your own sorption models
- Implement infinite activity measures (generalized log-normal)
- Connect to experimental data fitting

---

## Questions to Explore Later

1. Can we derive correction terms for weak spatial clustering?
2. How does intermediate phase diffusion modify the Lévy components?
3. What's the transition point where Monte Carlo becomes necessary?
4. Can we use Lévy moments to validate Monte Carlo convergence?
5. How do experimental chromatograms compare to Felinger predictions?

---

## Key References

- **Felinger et al. 1999**: Analytical Chem 71(20), 4472-4479
- **Pasti et al. 2005**: Analytical Chem 77(8), 2524-2535  
- **Kovalenko & Landes 2025**: J. Phys. Chem. C (rare site clustering)
- **Dondi 2002**: Analytical solutions discussion

---

**Remember**: The Lévy framework doesn't replace Monte Carlo - it complements it! Use Lévy for fast predictions and analytical insights, Monte Carlo for spatial effects and validation.

---

*End of Summary*
