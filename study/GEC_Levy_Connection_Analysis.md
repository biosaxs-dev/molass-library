# The Missing Link: How Pasti 2005 Connects Dondi 1992 to Lévy Awareness

**Date**: December 17, 2025  
**Analysis**: Connection between GEC CF proof (Dondi 1992) and Lévy-aware approach (Pasti 2005)

---

## Executive Summary

**The Discovery**: Pasti et al. (2005) explicitly shows that the Dondi 1992 GEC proof is **implicitly doing Lévy mathematics**. They:
1. Start with the **Lévy canonical representation** (Lévy-Khintchine theorem)
2. **Derive** the GEC model as a special case
3. Prove that the Dondi 1992 approach was "Lévy-unaware Lévy mathematics"

This document analyzes this connection in detail.

---

## Reference Chain

```
Dondi et al. 1992 [Ref 8 in Pasti 2005]
    "Theoretical Advancement in Chromatography..."
    NATO ASI Series C, Vol. 383, pp 173-210
    ↓
    Derives GEC CF using log-exp transformation
    (implicitly using compound Poisson = Lévy process)
    
Dondi et al. 2002
    "Stochastic theory of SEC by CF approach"
    J. Chromatogr. A, 943, 185-207
    ↓
    Cites [25] = Dondi 1992 for CF proof
    Uses result but doesn't invoke Lévy theorems
    
Pasti et al. 2005
    "Single-Molecule Observation...by Lévy Process"
    Anal. Chem. 77, 2524-2535
    ↓
    EXPLICIT Lévy-Khintchine invocation
    Shows GEC is special case of Lévy canonical form
```

---

## The Lévy Canonical Representation (Pasti 2005, Appendix I)

### Equation I-1: The Master Formula

Pasti 2005 starts with **Lévy's canonical representation**:

$$\ln \Phi(T; \omega | t) = t\left\{iv\omega - \frac{\sigma^2\omega^2}{2} + \int [e^{i\omega u} - 1] M(du)\right\}$$

Where:
- **$t$** = "clock time" (analogous to $t_m$ in chromatography)
- **$T$** = random variable (analogous to $t_s$)
- **$iv\omega$** = "shifting" (drift) component
- **$-\sigma^2\omega^2/2$** = "Brownian" (Gaussian) component
- **$\int [e^{i\omega u} - 1] M(du)$** = "Poisson" (jump) component
- **$M(du)$** = Lévy spectral measure (differential)

### The Three Independent Components

**Key insight** (from Pasti p. 2533):
> "The three above-mentioned contributions add stochastically and **independently**, under the same running time $t$."

This is **Lévy-Itô decomposition** - the components are guaranteed independent!

---

## Deriving GEC from Lévy Canonical Form

### Step 1: Specialization to Chromatography (Pasti Eq. I-2)

**Assumptions:**
1. $t = t_m$ (mobile phase time = "clock")
2. $v = 1$ (same clock for mobile and stationary phase)
3. $\sigma^2 = 0$ (no Brownian component, pure jump process)
4. $u = \tau_S$ (jump size = sorption time)

**Result:**
$$\ln \Phi(t_r; \omega | t_m) = i\omega t_m + t_m \int_0^\infty [e^{i\omega\tau_S} - 1] M(d\tau_S)$$

This is **Pasti Eq. I-2**, corresponding to **Dondi 2002 Eq. 25b**!

### Step 2: Exponential Lévy Measure (Pasti Eq. I-4)

For **GEC model**, the Lévy measure is exponential:

$$M(d\tau_S) = \frac{\lambda}{\bar{\tau}_S} e^{-\tau_S/\bar{\tau}_S} d\tau_S$$

Where:
- $\lambda = \bar{n}_p$ (mean number of sorption events)
- $\bar{\tau}_S$ (mean sorption time)

**Key observation**: This is the Lévy measure for compound Poisson with exponential jumps!

### Step 3: Evaluate the Integral (Pasti Eq. I-5, I-6)

**Pasti Eq. I-5:**
$$\ln \Phi_{\tau_S,C}(t_r; \omega | t_m) = t_m i\omega + t_m \lambda \int_0^\infty \left[e^{i\omega\tau_S} - 1\right] \frac{1}{\bar{\tau}_S} e^{-\tau_S/\bar{\tau}_S} d\tau_S$$

**Evaluating the integral:**
$$\int_0^\infty e^{i\omega\tau_S} \frac{1}{\bar{\tau}_S} e^{-\tau_S/\bar{\tau}_S} d\tau_S = \frac{1}{1 - i\omega\bar{\tau}_S}$$

Therefore:
$$\int_0^\infty \left[e^{i\omega\tau_S} - 1\right] \frac{1}{\bar{\tau}_S} e^{-\tau_S/\bar{\tau}_S} d\tau_S = \frac{1}{1 - i\omega\bar{\tau}_S} - 1$$

**Pasti Eq. I-6:**
$$\ln \Phi_{\tau_S,C}(t_r; \omega | t_m) = t_m i\omega + \bar{r}_m \left(\frac{1}{1 - i\omega\bar{\tau}_S} - 1\right)$$

where $\bar{r}_m = t_m \lambda = \bar{n}_p$ (using Eq. 4b from Pasti)

### Step 4: Remove Drift, Get GEC CF (Pasti Eq. I-7)

**Remove the drift term** ($t_m i\omega$) and set $t_m = t_M$:

$$\Phi_{\tau_S,C}(t_S; \omega | t_M) = \exp\left[\bar{r}_M\left(\frac{1}{1 - i\omega\bar{\tau}_S} - 1\right)\right]$$

**This is EXACTLY Dondi 2002 Eq. 43!**

$$\phi_{t_p}(\xi; r, d) = \exp\left[\bar{n}_p(r,d)\left(\frac{1}{1 - i\xi\bar{t}_p(r,d)} - 1\right)\right]$$

---

## The Proof Comparison Table

| Step | Dondi 1992 "Chromatographic-First" | Pasti 2005 "Lévy-First" |
|------|-------------------------------------|-------------------------|
| **Starting Point** | Chromatographic trajectories (Fig. 2) | Lévy canonical representation (Eq. I-1) |
| **Recognition** | Compound Poisson structure | **Invoke Lévy-Khintchine theorem** |
| **Method** | Log-exp transformation + convolution | **Specialize canonical form** |
| **Key Equation** | $\phi_{s,tot}(\xi) = \phi_{n,tot}[\ln(\phi_s(\xi))/i]$ | $\ln \Phi = t\int [e^{i\omega u} - 1] M(du)$ |
| **Exponential Sorption** | Derive CF: $\phi_s = 1/(1-i\xi\bar{t}_p)$ | **Apply exponential Lévy measure** |
| **Poisson Entries** | Derive CF: $\phi_n = \exp\{\bar{n}[e^{i\xi} - 1]\}$ | Inherent in $t_m \lambda$ structure |
| **Final Result** | Eq. 43 (derived) | Eq. I-7 (**theorem application**) |
| **Validation** | None explicit | Infinite divisibility guaranteed |
| **Variance** | Derive from 2nd derivative | **Lévy-Itô: automatic independence** |

---

## What Pasti 2005 Makes Explicit

### 1. **The Lévy Triplet Identification**

Pasti explicitly identifies the **Lévy-Khintchine triplet** for GEC:

```
(γ, σ², ν) for GEC chromatography:
```

- **γ** (drift): $v = 1$ → $\gamma = t_m$ (mobile phase time)
- **σ²** (Brownian): $\sigma^2 = 0$ (no diffusion in basic GEC)
- **ν** (Lévy measure): $M(d\tau_S) = (\lambda/\bar{\tau}_S) e^{-\tau_S/\bar{\tau}_S} d\tau_S$

**Dondi 1992 never explicitly identifies this triplet** - it's implicit in the derivation.

### 2. **The Independence Guarantee**

**Pasti p. 2533** (emphasis added):
> "The three above-mentioned contributions add stochastically and **independently**, under the same running time $t$."

**This is Lévy-Itô theorem!** It guarantees:
- Mobile phase (drift) independent of stationary phase (jumps)
- Different sorption events independent of each other
- **No proof needed** - it's theorem-guaranteed!

**Dondi 1992**: Assumes independence, proves variance addition from scratch (Eq. 58c)

**Pasti 2005**: Independence is **automatic** from Lévy-Itô decomposition

### 3. **Extension to Discrete Distributions**

**Pasti Eq. 16** (discrete Lévy measure):

$$\Phi_{\tau_S,D}(t_S; \omega | t_M) = \exp\left\{\bar{r}_M \sum_{i=1}^k [e^{i\omega\tau_{S,i}} - 1] \Delta F(\tau_{S,i})\right\}$$

Where $\Delta F(\tau_{S,i})$ are **observed probabilities** from single-molecule experiments!

**Key insight**: The Lévy framework naturally handles:
- Continuous distributions (exponential, gamma, etc.)
- Discrete distributions (experimental data)
- **Mixed** continuous + discrete (Eq. 22: NS + S sites)

**Dondi 1992** doesn't explicitly address discrete distributions - requires new derivation.

### 4. **The Retention Factor from Lévy Measure**

**Pasti Eq. 28d** (brilliant insight):

$$k' = \int_0^\infty \tau_S M(d\tau_S)$$

The retention factor is **the first moment of the Lévy spectral measure**!

This is **theorem-based**, not derived from chromatography:
- For continuous: $k' = \lambda \bar{\tau}_S$ (Eq. 28a)
- For discrete: $k' = \lambda \sum_i \tau_{S,i} \Delta F(\tau_{S,i})$ (Eq. 28b)
- For mixed: $k' = \lambda[\bar{\tau}_{S,NS} F_{NS} + \sum_i \tau_{S,i} \Delta F_S(\tau_{S,i})]$ (Eq. 28c)

**No chromatographic derivation needed** - it's the definition of the Lévy measure!

---

## The "Lévy Awareness Spectrum" Revealed

### Level 0: Formula-Based (Pre-Dondi 1992)
- Use CF formula for specific cases
- No general framework

### Level 1: Implicitly Lévy (Dondi 1992)
- ✅ Recognize compound process structure
- ✅ Use log-exp transformation (infinite divisibility)
- ✅ Derive general solutions
- ❌ Don't invoke Lévy-Khintchine by name
- ❌ Don't identify triplet (γ, σ², ν)
- ❌ Prove independence from scratch

**Status**: "Doing Lévy math without knowing it"

### Level 2: Partially Aware (Dondi 2002)
- ✅ Cite [25] for CF proof
- ✅ Recognize "s.i.i. processes" (stationary independent increments)
- ❌ Still don't invoke Lévy theorems explicitly
- ❌ Don't use Lévy triplet framework

**Status**: "Aware of Lévy properties but not using Lévy theorems"

### Level 3: Fully Lévy-Aware (Pasti 2005)
- ✅ **Start with Lévy canonical representation**
- ✅ **Invoke Lévy-Khintchine theorem explicitly** (refs 26-30)
- ✅ **Identify Lévy triplet** (γ, σ², ν)
- ✅ **Apply Lévy-Itô decomposition** (independence automatic)
- ✅ **Extend naturally** to discrete, mixed cases
- ✅ **Validation built-in** (infinite divisibility)

**Status**: "Theorem-first approach - trust and exploit"

---

## Practical Implications for Implementation

### The Dondi 1992 Way (Chromatographic-First)

```python
class GEC_Dondi1992:
    """Derived from chromatographic trajectories."""
    
    def __init__(self, n_bar, tau_bar):
        self.n_bar = n_bar
        self.tau_bar = tau_bar
    
    def characteristic_function(self, omega):
        """Derived via log-exp transformation (Eq. 46b, 52a)."""
        # Step 1: Derive Poisson CF
        phi_n = np.exp(self.n_bar * (np.exp(1j * omega) - 1))
        
        # Step 2: Derive exponential CF
        phi_s = 1 / (1 - 1j * omega * self.tau_bar)
        
        # Step 3: Apply log-exp transformation
        log_phi_s = np.log(phi_s)
        phi_total = phi_n(log_phi_s / 1j)  # Substitution!
        
        return phi_total
    
    def variance(self):
        """Derive from 2nd derivative (Eq. 58c)."""
        # Must prove: σ² = σ²_entries + σ²_sorption
        var_entries = self.n_bar  # Poisson variance
        var_sorption = self.n_bar * (self.tau_bar**2)  # Exponential variance
        
        # Prove independence to add
        return var_entries * (self.tau_bar**2) + var_sorption
```

### The Pasti 2005 Way (Lévy-First)

```python
class GEC_Pasti2005:
    """Lévy canonical representation approach."""
    
    def __init__(self, n_bar, tau_bar):
        self.n_bar = n_bar
        self.tau_bar = tau_bar
        
        # Validate Lévy triplet constraints
        assert n_bar >= 0, "Poisson rate must be non-negative"
        assert tau_bar > 0, "Mean sorption time must be positive"
    
    @property
    def levy_triplet(self):
        """Extract (γ, σ², ν) - theorem guarantees uniqueness."""
        return {
            'gamma': 0,  # No drift in pure sorption model
            'sigma_squared': 0,  # No Brownian (σ²=0 in Pasti Eq. I-2)
            'lambda': self.n_bar,  # Poisson rate
            'levy_measure': ExponentialMeasure(self.tau_bar)
        }
    
    def characteristic_function(self, omega):
        """Direct application of Lévy-Khintchine (Pasti Eq. I-7).
        
        NO DERIVATION - Theorem guarantees this form!
        """
        triplet = self.levy_triplet
        
        # Lévy-Khintchine formula: exp[t∫(e^(iωu) - 1)M(du)]
        # For exponential measure: integral = 1/(1-iωτ̄) - 1
        log_phi = triplet['lambda'] * (
            1 / (1 - 1j * omega * self.tau_bar) - 1
        )
        
        return np.exp(log_phi)
    
    def moments_from_levy_measure(self):
        """By theorem: E[X] = ∫u M(du), Var[X] = ∫u² M(du)."""
        triplet = self.levy_triplet
        
        # For exponential Lévy measure (Pasti Eq. 28a):
        mean = triplet['lambda'] * self.tau_bar  # E[τ]
        var = triplet['lambda'] * (2 * self.tau_bar**2)  # E[τ²] for exponential
        
        return mean, var  # NO DERIVATION - theorem!
    
    def retention_factor(self):
        """k' = first moment of Lévy measure (Pasti Eq. 28d)."""
        # This is the DEFINITION from Lévy measure, not derived!
        return self.n_bar * self.tau_bar
```

### The Key Difference

```python
# Dondi 1992 approach:
variance_dondi = derive_from_second_derivative_of_CF()
# - Requires proof
# - Requires independence proof
# - Hard to extend

# Pasti 2005 approach:
variance_pasti = integrate_u_squared_over_levy_measure()
# - Theorem-guaranteed
# - Independence automatic (Lévy-Itô)
# - Extends naturally to any Lévy measure
```

---

## Extension: Beyond GEC

### Pasti 2005 Eq. 22: Mixed NS + S Sites

$$\Phi_{NS+S} = \underbrace{\exp\left[\bar{r}_M \left(\frac{1}{1-i\omega\bar{\tau}_{S,NS}} - 1\right) F_{NS}\right]}_{\text{Continuous (NS)}} \cdot \underbrace{\exp\left[\bar{r}_M \sum_{i=1}^k [e^{i\omega\tau_{S,i}} - 1] \Delta F_S(\tau_{S,i})\right]}_{\text{Discrete (S)}}$$

**Lévy-aware insight**: This is just **two independent Lévy processes** multiplying!

By **Lévy-Itô theorem**:
- CF_total = CF_NS × CF_S (in frequency domain)
- log φ_total = log φ_NS + log φ_S (cumulants add)
- Var_total = Var_NS + Var_S (variances add)

**No proof needed** - it's guaranteed by theorem!

### Dondi 1992 Approach Would Require:
1. Derive mixed CF from scratch
2. Prove components are independent
3. Prove variances add
4. Validate result

### Pasti 2005 Approach:
1. ✅ Recognize both are Lévy processes
2. ✅ Multiply CFs (theorem guarantees independence)
3. ✅ Done!

---

## Citations and Cross-References

### How Pasti 2005 Cites Dondi 1992

**Reference [8] in Pasti 2005:**
> Dondi, F.; Blo, G.; Remelli, M.; Reschiglian, P. In *Theoretical Advancement in Chromatography and Related Separation Techniques*; Dondi, F., Guiochon, G., Eds.; NATO ASI Series C. Vol. 383; Kluwer Academic Publisher: Dordrecht, 1992; pp 173-210.

**Used for**:
- CF method background (introduction)
- "Randomization" technique for mobile-phase dispersion (Appendix I)
- Reference point for deriving GEC from Lévy canonical form

### How They Frame the Advance

**Pasti 2005, p. 2524** (emphasis added):
> "This **renewed stochastic approach** is based on the so-called **Lévy canonical description** of stochastic processes and appears to be **the most general basis** for handling separation processes from a stochastic point of view."

**Translation**: "Dondi 1992 had the right math, but Lévy formalism is the proper foundation."

---

## The Conceptual Evolution

### 1955-1992: Chromatographic Derivation Era
- Giddings-Eyring (1955): Specific exponential + Poisson case
- McQuarrie (1963): Mathematical refinement
- **Dondi et al. (1992)**: General CF method, compound processes
  - **Achievement**: General framework for any distributions
  - **Limitation**: Each case requires new derivation

### 2002: Recognition of Lévy Properties
- Dondi et al. (2002): SEC with CF method
  - Recognizes "s.i.i. processes" (stationary independent increments)
  - Cites [25] for CF proof
  - **Still no explicit Lévy invocation**

### 2005: Lévy-First Revolution
- **Pasti et al. (2005)**: Explicit Lévy canonical representation
  - **Achievement**: Theorem-first approach
  - **Impact**: Natural extension to discrete, mixed distributions
  - **Foundation**: Links chromatography to single-molecule observations

---

## Summary: What We Learned

### The Missing Link Was Found!

**Question**: How does the Dondi 1992 GEC proof relate to Lévy awareness?

**Answer**: 
1. ✅ **Pasti 2005 explicitly shows** Dondi 1992 was doing Lévy math implicitly
2. ✅ **They cite Dondi 1992** (reference [8]) for the CF method
3. ✅ **They derive GEC from Lévy-Khintchine** (Appendix I, Eq. I-7)
4. ✅ **They make the connection explicit** - GEC is compound Poisson = special Lévy process

### The Awareness Spectrum Confirmed

```
1992 Dondi          2002 Dondi          2005 Pasti
    ↓                   ↓                    ↓
Implicitly       Recognizes Lévy      Explicitly
Lévy             properties           Lévy-first
(compound        (s.i.i. processes)   (canonical
 Poisson)                             representation)
```

### Practical Takeaway

**For your SDM implementation**:
- You can **rewrite** using Lévy triplet (γ, σ², ν)
- You should **invoke theorems** instead of re-deriving
- You will **extend naturally** to multi-site, discrete distributions
- You get **validation built-in** (infinite divisibility)

**The Pasti 2005 paper is the Rosetta Stone** - it translates Dondi's chromatographic CF method into modern Lévy process language.

---

## References

1. **Giddings, J.C., & Eyring, H.** (1955). J. Phys. Chem., 59, 416-421.

2. **Dondi, F., Blo, G., Remelli, M., & Reschiglian, P.** (1992). In *Theoretical Advancement in Chromatography*, NATO ASI Series C, Vol. 383, pp. 173-210.

3. **Dondi, F., Cavazzini, A., Remelli, M., & Felinger, A.** (2002). J. Chromatogr. A, 943, 185-207.

4. **Pasti, L., Cavazzini, A., Felinger, A., Martin, M., & Dondi, F.** (2005). Anal. Chem., 77, 2524-2535.

5. **Lévy, P.** (1954). *Théorie de l'Addition des Variables Aléatoires*, Gauthier-Villars, Paris.

6. **Sato, K.-I.** (2002). *Lévy Processes and Infinitely Divisible Distributions*, Cambridge University Press.

---

**Document Created**: December 17, 2025  
**Purpose**: Analyze the connection between Dondi 1992 GEC proof and Pasti 2005 Lévy-aware approach  
**Conclusion**: The missing link has been found - Pasti 2005 explicitly shows Dondi 1992 was "Lévy-unaware Lévy mathematics"
