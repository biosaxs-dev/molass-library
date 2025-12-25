# Comparison: Dondi 1992 Derivation vs Lévy Theorem Proofs

**Date**: December 17, 2025  
**Purpose**: Compare what Dondi 1992 derives from first principles versus what Lévy theorems provide "for free"

---

## Where to Find the Theorem Statements

### In This Repository:

1. **[SESSION_2025-12-16_levy_awareness.md](SESSION_2025-12-16_levy_awareness.md)**
   - Lines ~23-52: Wikipedia definition of Lévy processes
   - Lévy-Khintchine representation formula
   - Lévy-Itô decomposition formula

2. **[GEC_Levy_Connection_Analysis.md](GEC_Levy_Connection_Analysis.md)**
   - Pasti 2005's application of Lévy canonical form (Eq. I-1)
   - How GEC is derived from Lévy-Khintchine

3. **[GEC_CF_Proof_Summary.md](GEC_CF_Proof_Summary.md)**
   - Dondi 1992 derivation steps
   - The log-exp transformation method

### Standard References for Lévy Theorem Proofs:

**Note**: The actual **proofs** of Lévy theorems are not in the chromatography papers. They're found in:

1. **Sato, K.-I.** (1999). *Lévy Processes and Infinitely Divisible Distributions*. Cambridge University Press.
   - Chapter 2: Lévy-Khintchine representation proof
   - Chapter 4: Lévy-Itô decomposition proof

2. **Bertoin, J.** (1996). *Lévy Processes*. Cambridge University Press.
   - Chapter I: Canonical representation proofs

3. **Applebaum, D.** (2009). *Lévy Processes and Stochastic Calculus* (2nd ed.). Cambridge University Press.
   - Chapter 2: Complete proofs of Lévy theorems

4. **Pasti 2005 references** [26-31]:
   - [26] Lévy, P. (1954). *Théorie de l'Addition des Variables Aléatoires*
   - [27] Sato (above)
   - [28] Bertoin (above)
   - [29] De Finetti probability theory
   - [30] Barndorff-Nielsen et al. (2001). *Lévy Processes: Theory and Applications*

---

## The Comparison Table

| What Needs to Be Established | Dondi 1992 Approach | Lévy Theorems Provide |
|------------------------------|---------------------|----------------------|
| **1. Characteristic Function Form** | | |
| For compound Poisson process | **Derives** via log-exp transformation (Eq. 46b) | **Theorem**: Lévy-Khintchine guarantees form |
| Specific steps | 1. Start with mixture: $\phi = \sum_n p_n \phi_s^n$ | Already known: $\phi = \exp[t\int(e^{i\omega u}-1)\nu(du)]$ |
| | 2. Apply $x^r = \exp[r\ln x]$ | |
| | 3. Recognize as CF of n with transformed variable | |
| | 4. Prove it works | |
| Mathematical depth | ~3 pages of derivation | **Direct application** of theorem |
| **2. Independence of Components** | | |
| Entry process vs sorption time | **Assumes** then validates | **Theorem**: Lévy-Itô guarantees independence |
| Proof required | Must show processes don't interfere | **No proof needed** - theorem property |
| Evidence in paper | "It can be shown..." (implied) | Stated as axiom of Lévy decomposition |
| **3. Variance Addition** | | |
| Total variance formula | **Derives** from 2nd derivative (Eq. 58) | **Theorem**: Independent Lévy components → variances add |
| Derivation | $\sigma^2_{tot} = \sigma^2_n \Delta t_s^2 + \bar{n}\sigma^2_s$ | $\text{Var}[X] = \sum_i \text{Var}[X_i]$ (automatic) |
| Mathematical work | Take derivatives, apply cumulant rules | **Zero** - it's the definition |
| **4. Linear Scaling with Column Length** | | |
| $\psi(L) = L \cdot [\text{per-unit process}]$ | **Observes** and proves (Eq. 52c) | **Theorem**: Stationary increments property |
| Significance | Identifies as "s.i.i. process" | This IS the Lévy process definition |
| Work required | Prove from convolution structure | **Recognized** as Lévy property |
| **5. Infinite Divisibility** | | |
| $\phi(\omega) = [\phi(\omega/n)]^n$ | **Uses** implicitly (never validates) | **Theorem**: Required for Lévy process |
| Validation | Not checked in paper | **Must validate** to use Lévy-Khintchine |
| Implementation | Assumes it holds | **Check before** applying theorem |
| **6. Moment Calculations** | | |
| Mean, variance, skewness | **Derive** from CF derivatives (Eq. 21, 23) | **Theorem**: $E[X^k] = \int u^k \nu(du)$ |
| For mean | Take derivative: $\psi'(0)/i$ | **Direct**: $\bar{n}\bar{\tau}$ (first moment of measure) |
| For variance | Take 2nd derivative: $-\psi''(0)$ | **Direct**: $\bar{n}E[\tau^2]$ (second moment of measure) |
| Computational cost | Symbolic differentiation needed | **Analytical formula** |
| **7. Extension to Multiple Sites** | | |
| Heterogeneous stationary phase | New derivation needed | **Theorem**: Sum of Lévy processes is Lévy |
| CF construction | Re-derive mixture process | **Multiply** CFs (independence guaranteed) |
| Variance | Re-derive addition | **Add** variances (automatic) |
| **8. Validation of Result** | | |
| How to check if CF is valid | Not addressed | **Theorem**: Check (γ, σ², ν) constraints |
| Constraints | Implicit in derivation | **Explicit**: $\int \min(1, u^2)\nu(du) < \infty$ |
| Error detection | Hard to catch invalid CF | **Built-in** validation from triplet |

---

## Detailed Comparison: Key Results

### Result 1: The CF Form

#### What Dondi 1992 Derives (Eq. 46b):

**Starting point**: Mixture of n-fold convolutions
$$\phi_{s,tot}(\xi) = \sum_n p_n [\phi_s(\xi)]^n$$

**Derivation** (summarized):
1. Apply identity: $x^n = \exp[n \ln x]$
2. Rewrite: $\phi_{s,tot}(\xi) = \sum_n p_n \exp\left[n \cdot \frac{\ln \phi_s(\xi)}{i} \cdot i\right]$
3. Recognize RHS as CF of n with auxiliary variable $\ln(\phi_s(\xi))/i$
4. Substitute to get: $\phi_{s,tot}(\xi) = \phi_{n,tot}\left[\frac{\ln \phi_s(\xi)}{i}\right]$

**Mathematical tools used**:
- Convolution theorem (CF of sum = product of CFs)
- Logarithm properties
- Pattern recognition
- Substitution

**Pages of work**: ~2 pages in Dondi 1992 (pp. 186-187)

#### What Lévy-Khintchine Theorem Provides:

**Theorem statement** (from Sato 1999, Theorem 8.1):

> For any infinitely divisible distribution on $\mathbb{R}$, there exists a unique triplet $(γ, σ^2, ν)$ such that its characteristic function is:
> $$\phi(\omega) = \exp\left[i\gamma\omega - \frac{\sigma^2\omega^2}{2} + \int_{-\infty}^{\infty} (e^{i\omega u} - 1 - i\omega u \mathbf{1}_{|u|<1}) \nu(du)\right]$$

**For compound Poisson** (jump process only, $\gamma=0$, $\sigma^2=0$):
$$\phi(\omega) = \exp\left[\lambda \int_0^{\infty} (e^{i\omega u} - 1) \nu(du)\right]$$

where $\lambda = \int \nu(du)$ is the Poisson rate.

**Mathematical tools needed**:
- **Recognition** that process is infinitely divisible
- **Identification** of the Lévy measure ν

**Pages of work**: **Zero** - it's theorem application!

**The proof** of Lévy-Khintchine is ~20 pages in Sato 1999 (pp. 36-56), involving:
- Continuity theorems
- Convergence of infinitely divisible laws
- Fourier analysis
- Measure theory

**Dondi doesn't need this proof** - the theorem is already proven!

---

### Result 2: Independence and Variance Addition

#### What Dondi 1992 Derives (Eq. 58):

**Starting from**: $\psi_{tot}(\xi) = \psi_n[\psi_s(\xi)/i]$

**Taking second derivative**:
$$K_{2,s,tot} = K_{2,n,tot} K_{1,s}^2 + K_{1,n,tot} K_{2,s}$$

**Interpreting**:
$$\sigma^2_{s,tot} = \sigma^2_{n,tot} \cdot (\Delta t_s)^2 + \bar{n} \cdot \sigma^2_s$$

**Components**:
- First term: "entry process dispersion" 
- Second term: "stationary phase dispersion"

**Claim** (Dondi 1992, p. 190-191):
> "The first term is identified as the 'entry process dispersion' term... The second term is related to the stationary phase sorption process..."

**Proof strategy**: Derive from cumulant properties and CF derivatives.

**Issue**: Why do these add? **Implicitly assumes independence** but doesn't prove it from first principles!

#### What Lévy-Itô Theorem Provides:

**Theorem statement** (from Bertoin 1996, Theorem I.2):

> Any Lévy process $X_t$ can be decomposed as:
> $$X_t = \gamma t + \sigma B_t + \int_{|u|<1} u \tilde{N}(t, du) + \int_{|u|\geq 1} u N(t, du)$$
> where:
> - $\gamma t$ = deterministic drift
> - $\sigma B_t$ = Brownian component (independent)
> - Jumps < 1: compensated Poisson process (independent)
> - Jumps ≥ 1: Poisson process (independent)
>
> **All components are mutually independent!**

**For GEC** (compound Poisson = jumps only):
$$X_t = \sum_{i=1}^{N_t} \tau_i$$

where $N_t$ = Poisson process (rate λ), $\tau_i$ = iid jumps

**Independence**: Guaranteed by theorem construction!

**Variance**:
$$\text{Var}[X_t] = \text{Var}[N_t] \cdot E[\tau]^2 + E[N_t] \cdot \text{Var}[\tau]$$

**Proof of independence**: Built into the theorem (see Bertoin 1996, pp. 14-18)

**Dondi doesn't prove independence** - assumes it, then validates via variance formula. **Lévy-Itô guarantees it!**

---

### Result 3: Moments from Lévy Measure

#### What Dondi 1992 Derives (Eq. 56-57):

**Mean** (Eq. 56b):
$$\bar{t}_p = \bar{n} \cdot \bar{\tau}_s$$

**Derivation**:
1. Take first derivative of $\psi_{tot}(\xi) = \psi_n[\psi_s(\xi)/i]$
2. Apply chain rule
3. Evaluate at $\xi = 0$
4. Use $\psi(0) = 0$ and $\psi'(0) = i\mu$
5. Simplify

**Called "Wald relation"** - presented as special result for compound processes.

**Variance** (Eq. 58c):
$$\sigma^2_{tot} = \sigma^2_n (\Delta t_s)^2 + \bar{n} \sigma^2_s$$

**Derivation**: Similar (2nd derivative, chain rule, evaluate)

#### What Lévy Measure Provides:

**Definition** (from measure theory):

For Lévy measure $\nu(du)$:
$$E[X_t] = t \left[\gamma + \int u \nu(du)\right]$$
$$\text{Var}[X_t] = t \left[\sigma^2 + \int u^2 \nu(du)\right]$$

**For compound Poisson** ($\gamma = 0$, $\sigma^2 = 0$):
$$E[X_t] = t \lambda \int u \nu(du) = t \lambda E[\tau]$$
$$\text{Var}[X_t] = t \lambda \int u^2 \nu(du) = t \lambda E[\tau^2]$$

**With** $t = t_m$, $\lambda = \bar{n}/t_m$:
$$E[X] = \bar{n} E[\tau]$$
$$\text{Var}[X] = \bar{n} E[\tau^2]$$

**For exponential** $\tau \sim \text{Exp}(1/\bar{\tau})$:
- $E[\tau] = \bar{\tau}$
- $E[\tau^2] = 2\bar{\tau}^2$

Therefore:
$$E[X] = \bar{n} \bar{\tau}$$
$$\text{Var}[X] = \bar{n} \cdot 2\bar{\tau}^2$$

**This is just the definition of moments from a measure!**

**No derivation needed** - it's measure theory 101:
$$E[g(X)] = \int g(u) \nu(du)$$

Set $g(u) = u$ for mean, $g(u) = u^2$ for second moment.

---

### Result 4: Linear Scaling Property

#### What Dondi 1992 Observes (Eq. 52c):

**Equation**:
$$\psi_{s,tot}(L, \xi) = L \frac{k_m}{V_m} [\phi_s(\xi) - 1]$$

**Statement** (Dondi 1992, p. 189):
> "The linear dependence of the 2ndCF on the continuous parameter L, the column length... This mathematical property is fundamental since it allows us to place this model within the important class of stochastic processes with independent and stationary increments (briefly s.i.i. process)..."

**Observation**: They recognize this as important but don't fully exploit it as the **definition** of a Lévy process.

#### What "Stationary Increments" Property Means:

**Lévy Process Definition** (Property 3):

> A stochastic process $\{X_t\}$ has **stationary increments** if:
> $$X_{t+s} - X_t \stackrel{d}{=} X_s - X_0 = X_s$$
> for all $t, s \geq 0$.

**Implication for CF**:
$$\phi_{X_{t+s} - X_t}(\omega) = \phi_{X_s}(\omega)$$

**For Lévy processes**, this leads to:
$$\phi_{X_t}(\omega) = [\phi_{X_1}(\omega)]^t$$

In log space:
$$\ln \phi_{X_t}(\omega) = t \cdot \ln \phi_{X_1}(\omega)$$

**This is exactly** the linear scaling Dondi observes!

**It's not a derived property** - it's the **definition** of stationary increments!

**Dondi**: Derives → Observes → "Oh, this is s.i.i. property"  
**Lévy approach**: Recognize s.i.i. → Linear scaling is automatic

---

## The Proof Structure Comparison

### Dondi 1992 Proof Structure:

```
Chromatographic Trajectories (Fig. 2)
    ↓
Random walk model (n sorption steps, each time τ)
    ↓
Mixture process: different n for different molecules
    ↓
CF of mixture: Σ pₙ [φ_s]ⁿ
    ↓
Log-exp transformation: Σ pₙ exp[n ln φ_s / i · i]
    ↓
Pattern recognition: This is φₙ[ln φ_s / i]
    ↓
Specialize to Poisson: φₙ(ξ) = exp{n̄[e^(iξ) - 1]}
    ↓
Substitute: φₜₒₜ = exp{n̄[φ_s - 1]}
    ↓
Specialize to exponential: φ_s = 1/(1 - iξτ̄)
    ↓
Final result: φ = exp{n̄[1/(1-iξτ̄) - 1]}
    ↓
Derive moments by taking derivatives
    ↓
Observe linear scaling → "It's s.i.i. process!"
```

**Key characteristics**:
- ✅ Builds understanding from physical process
- ✅ Self-contained (doesn't require external theorems)
- ❌ Lots of derivation work
- ❌ Hard to extend to new cases
- ❌ Independence assumed, not proven
- ❌ No validation framework

**Total work**: ~15 pages of derivations (Dondi 1992, pp. 173-188)

### Lévy Theorem-First Structure:

```
Observe chromatographic process
    ↓
Recognize: Independent increments? ✓
Recognize: Stationary increments? ✓
Recognize: Càdlàg paths? ✓
    ↓
Conclusion: It's a Lévy process!
    ↓
Invoke Lévy-Khintchine Theorem
    ↓
Identify Lévy triplet (γ, σ², ν):
  - γ = 0 (no drift in pure sorption)
  - σ² = 0 (no Brownian component)
  - ν = exponential measure for GEC
    ↓
Apply theorem: φ = exp[∫(e^(iωu) - 1)ν(du)]
    ↓
Evaluate integral for exponential ν
    ↓
Result: φ = exp{n̄[1/(1-iξτ̄) - 1]}
    ↓
Moments by Lévy measure: E[X^k] = ∫u^k ν(du)
    ↓
Independence by Lévy-Itô: Components add
    ↓
Validation: Check ∫min(1,u²)ν(du) < ∞
```

**Key characteristics**:
- ✅ **Zero derivation** - all theorems
- ✅ **Built-in validation** (triplet constraints)
- ✅ **Independence guaranteed** (Lévy-Itô)
- ✅ **Easy extension** (change ν, done!)
- ✅ **Modular** (add Brownian? just set σ² ≠ 0)
- ❌ Requires knowing Lévy theory
- ❌ Less intuitive for chromatographers

**Total work**: Recognition (~1 page) + Theorem application (~2 pages)

---

## What Each Approach Proves vs Assumes

| Aspect | Dondi 1992 | Lévy Theorems | Who Wins? |
|--------|-----------|---------------|-----------|
| **CF form for compound Poisson** | Derives from convolution | **Assumes** (Lévy-Khintchine proven elsewhere) | **Lévy** (use proven theorem) |
| **Independence of components** | **Assumes** (validates via variance) | **Proves** (Lévy-Itô decomposition) | **Lévy** (rigorously proven) |
| **Variance addition** | Derives from CF derivatives | **Automatic** from independence | **Lévy** (no work needed) |
| **Linear scaling** | Derives then observes | **Defines** Lévy process | **Lévy** (it's the starting point) |
| **Moments from measure** | Derives by differentiation | **Defines** measure | **Lévy** (it's measure theory) |
| **Physical intuition** | **Builds** from trajectories | Abstracts to process properties | **Dondi** (better understanding) |
| **Extension to new cases** | Re-derive everything | Change ν, apply theorem | **Lévy** (modular) |
| **Validation** | None explicit | **Built-in** (triplet constraints) | **Lévy** (error-proof) |

---

## The "Black Box" Trade-off

### Dondi 1992: "Glass Box"
- ✅ You see every step
- ✅ Build intuition from physical process
- ✅ Self-contained
- ❌ Labor-intensive
- ❌ Hard to extend
- ❌ Easy to make mistakes

### Lévy Theorems: "Theorem Box"
- ✅ Efficient (use proven results)
- ✅ Modular (easy to extend)
- ✅ Validated (theorem constraints)
- ❌ Need to trust theorems (20+ pages of proof)
- ❌ Less intuitive initially
- ✅ Once learned, very powerful

---

## Example: Adding a New Sorption Mechanism

### Dondi 1992 Approach:

**Task**: Add gamma-distributed sorption times instead of exponential

**Steps**:
1. Write gamma CF: $\phi_s(\xi) = [1/(1 - i\xi\theta)]^k$
2. Re-derive mixture CF (Eq. 46b still applies)
3. Substitute gamma CF into Poisson CF
4. Simplify: $\phi = \exp\{n[1/(1-i\xi\theta)^k - 1]\}$
5. **Re-derive moments** by differentiation
6. **Re-derive variance** formula
7. **Validate** that it still works

**Work**: ~3-5 pages of new derivations

### Lévy Theorem Approach:

**Task**: Add gamma-distributed sorption times

**Steps**:
1. **Change Lévy measure**: $\nu(du) = \frac{k}{\Gamma(k)\theta^k} u^{k-1} e^{-u/\theta} du$
2. **Apply Lévy-Khintchine**: $\phi = \exp[\lambda \int (e^{i\omega u} - 1)\nu(du)]$
3. **Evaluate integral**: (gamma measure → closed form)
4. **Done!**

**Moments**: $E[X^j] = \lambda \int u^j \nu(du)$ (just integrate!)  
**Variance**: Automatic from Lévy-Itô  
**Validation**: Check $\int \min(1, u^2)\nu(du) < \infty$ ✓

**Work**: Change one line of code!

```python
# Dondi approach
levy_measure = ExponentialMeasure(tau_bar)  # Old
levy_measure = GammaMeasure(k, theta)       # New - THAT'S IT!
# Everything else automatic from Lévy-Khintchine
```

---

## Summary: The Fundamental Difference

### Dondi 1992: Building the Ladder

**Approach**: Start from ground, build ladder rung by rung
- Rung 1: Random walk → CF
- Rung 2: Mixture process → log-exp
- Rung 3: Poisson entries → substitute
- Rung 4: Exponential sorption → evaluate
- Rung 5: Moments → differentiate
- Rung 6: Variance → cumulants

**Result**: You understand each step deeply  
**Cost**: ~15 pages to climb the ladder  
**Problem**: Need new ladder for each new building

### Lévy Theorems: Using the Elevator

**Approach**: Recognize building has elevator (Lévy process)
- Press button 1: Identify triplet (γ, σ², ν)
- Press button 2: Apply Lévy-Khintchine
- Arrive at top floor!

**Result**: Same answer, arrived efficiently  
**Cost**: Need to trust elevator manufacturer (theorem provers)  
**Advantage**: Same elevator works for ALL Lévy buildings

---

## Where to Find Full Theorem Proofs

### ✅ You HAVE (in your markdown files):

1. **Theorem statements**: [SESSION_2025-12-16_levy_awareness.md](SESSION_2025-12-16_levy_awareness.md)
2. **Dondi derivation**: [GEC_CF_Proof_Summary.md](GEC_CF_Proof_Summary.md)
3. **Pasti application**: [GEC_Levy_Connection_Analysis.md](GEC_Levy_Connection_Analysis.md)

### ❌ You DON'T HAVE (need textbooks):

1. **Lévy-Khintchine proof**: Sato (1999), pp. 36-56
2. **Lévy-Itô decomposition proof**: Bertoin (1996), pp. 14-18
3. **Infinite divisibility theory**: Feller Vol. II, Chapter XIII

### 💡 The Key Insight:

**You don't NEED the Lévy theorem proofs to use them!**

Just like you don't need to prove the Fourier transform exists before using FFT, you don't need to prove Lévy-Khintchine before applying it.

**Dondi 1992 essentially re-proves** a special case of Lévy-Khintchine without knowing it!  
**Pasti 2005 recognizes** this and invokes the general theorem instead.

---

## Practical Recommendation

For your SDM implementation:

### Phase 1: Understand Dondi (Done! ✓)
- Read the derivation
- Understand log-exp transformation
- Appreciate the physical intuition

### Phase 2: Recognize Lévy Structure
- Identify: It's compound Poisson = Lévy process
- Extract: Triplet (γ=0, σ²=0, ν=exponential)
- Validate: Check infinite divisibility

### Phase 3: Use Lévy Theorems
- **Don't re-derive** - invoke theorems
- Moments: Integrate against ν
- Variance: Lévy-Itô guarantees addition
- Extensions: Change ν, done!

### You've Achieved Phase 1 and 2!
Next: Implement Phase 3 (Lévy-aware code)

---

**Document Created**: December 17, 2025  
**Summary**: Dondi derives what Lévy theorems provide. Both reach same answer, but Lévy path is an elevator while Dondi builds the stairs!
