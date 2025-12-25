# Deriving the GEC Characteristic Function from Animation Objects: A Lévy-Aware Approach

**Author**: Molass Community  
**Date**: December 17, 2025  
**Purpose**: Explain what a Lévy process is and why "Lévy awareness" matters by deriving the monopore GEC characteristic function step-by-step using concrete objects from `ColumnSimulation.py`

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Animation Objects → Mathematical Symbols](#2-animation-objects--mathematical-symbols)
3. [What is a Lévy Process?](#3-what-is-a-lévy-process)
4. [Why Lévy Awareness Matters](#4-why-lévy-awareness-matters)
5. [Step-by-Step CF Derivation (Lévy-Aware)](#5-step-by-step-cf-derivation-lévy-aware)
6. [Comparison: Manual vs Lévy-Aware](#6-comparison-manual-vs-lévy-aware)
7. [Verification with Animation Data](#7-verification-with-animation-data)
8. [References](#8-references)

---

## 1. Introduction

The SEC animation in `molass/SEC/ColumnSimulation.py` simulates particles moving through a column with the following key features:

- **Three species**: Large (green), medium (blue), small (red)
- **Stochastic dynamics**: Random walk + grain adsorption/desorption
- **Size exclusion**: Larger particles are excluded from smaller pores

This document shows how to derive the **Giddings-Eyring-Carmichael (GEC) characteristic function** from these animation objects using a **Lévy process framework**, demonstrating why "Lévy awareness" provides mathematical shortcuts.

---

## 2. Animation Objects → Mathematical Symbols

### 2.1 The Fundamental Mapping

| **Animation Object** | **Code Variable** | **Math Symbol** | **Meaning** |
|---------------------|-------------------|-----------------|-------------|
| One particle trajectory | `pyv[k, :]` | $X_k(t)$ | One realization of Lévy process |
| Mobile/adsorbed state | `inmobile_states[k]` | Boolean | True = mobile, False = adsorbed |
| Grain attachment | `grain_references[k]` | Integer | -1 = mobile, j = adsorbed to grain j |
| Adsorption event | Transition: True → False | Point event | Poisson process event |
| Desorption event | Transition: False → True | Jump completion | End of "jump" in Lévy process |
| Adsorption duration | Frames while False | $\tau_{S,m}$ | mth jump size (time in grain) |
| # of adsorptions | Count of True → False | $r_M$ | Total # of jumps (Poisson) |
| Total adsorbed time | Sum of all durations | $t_S = \sum_m \tau_{S,m}$ | **Key random variable** |
| Retention time | Frame when $y \approx 0$ | $t_R = t_M + t_S$ | Chromatographic observable |

### 2.2 Critical Distinction

**Don't confuse:**
- `pyv[k, i]` = **spatial position** at frame i (y-coordinate)
- $t_S[k]$ = **cumulative adsorption time** (what GEC/Pasti models!)

The GEC model predicts the **distribution of $t_S$**, not the distribution of spatial positions directly.

---

## 3. What is a Lévy Process?

### 3.1 Definition (Animation-Friendly)

A **Lévy process** $X(t)$ is a stochastic process with:

1. **Independent increments**: What happens in `[i, i+1]` is independent of `[0, i]`
   - Animation: Future adsorptions don't depend on past history
   
2. **Stationary increments**: Distribution of $X(t+s) - X(s)$ depends only on $t$
   - Animation: Statistics don't change as particle moves down column
   
3. **Starts at zero**: $X(0) = 0$ almost surely
   - Animation: Total adsorbed time starts at zero
   
4. **Càdlàg paths**: Right-continuous with left limits
   - Animation: Instantaneous adsorption events (jumps)

### 3.2 Lévy-Khintchine Representation

**KEY THEOREM**: Any Lévy process has a characteristic function:

$$\phi(ω, t) = \exp\left[t \cdot \psi(ω)\right]$$

where the **Lévy exponent** $\psi(ω)$ has the canonical form:

$$\psi(ω) = i\gamma ω - \frac{\sigma^2 ω^2}{2} + \int_{\mathbb{R}} \left(e^{iωx} - 1 - iωx \mathbb{1}_{|x|<1}\right) \nu(dx)$$

**Components:**
- $\gamma$ = drift (deterministic trend)
- $\sigma^2$ = Brownian component (diffusion)
- $\nu(dx)$ = **Lévy measure** (jump distribution)

### 3.3 Compound Poisson Process (GEC Model)

The **GEC model** is a **Compound Poisson Process (CPP)**, a special Lévy process with:

- No drift: $\gamma = 0$
- No diffusion: $\sigma^2 = 0$
- Only jumps: Poisson($\lambda$) number of jumps, each with size from $F(\tau)$

**Animation interpretation:**
- $\lambda$ = rate of adsorption events (Poisson parameter)
- $F(\tau) = 1 - e^{-\tau/\bar{\tau}_S}$ = exponential jump size distribution (adsorption duration)

**CPP Characteristic Function:**

$$\phi_{CPP}(ω, t) = \exp\left[\lambda t \int_0^∞ (e^{iω\tau} - 1) f(\tau) d\tau\right]$$

where $f(\tau) = F'(\tau)$ is the jump size density.

---

## 4. Why Lévy Awareness Matters

### 4.1 The Problem Without Lévy Awareness

**Traditional approach (Giddings-Eyring 1955):**

1. Start with single-molecule trajectory
2. Model adsorption as renewal process
3. Derive distribution via convolutions:
   $$f_{t_S}(t) = \sum_{n=0}^∞ P(r_M = n) \cdot f_{\tau}^{*n}(t)$$
   where $*$ denotes convolution
4. Take Fourier transform to get CF
5. Manually compute moments from derivatives

**Challenges:**
- Convolutions are computationally expensive
- No insight into structural properties
- Hard to extend to complex models
- Easy to make algebraic mistakes

### 4.2 The Solution With Lévy Awareness

**Lévy-aware approach (Dondi 2002, Pasti 2005):**

1. **Recognize** the process structure:
   - Poisson # of events → CPP
   - Independent jumps → Lévy property
   
2. **Invoke** Lévy-Khintchine theorem:
   - CF must have form $\exp[t \cdot \psi(ω)]$
   - No need to derive from scratch!
   
3. **Apply** CPP formula directly:
   - Identify $\lambda$ (adsorption rate)
   - Identify $\nu(d\tau)$ (jump measure)
   - Plug into canonical form
   
4. **Compute** moments from cumulants:
   - $\kappa_1 = -i\psi'(0)$ = mean
   - $\kappa_2 = -\psi''(0)$ = variance
   - No need for repeated differentiation!

**Benefits:**
- ✅ **Fast**: Use proven formulas
- ✅ **Correct**: Theorem guarantees structure
- ✅ **Insightful**: See parameter roles clearly
- ✅ **Extensible**: Easy to add new jump types

---

## 5. Step-by-Step CF Derivation (Lévy-Aware)

### Step 1: Identify the Process from Animation

**Animation observations:**

```python
# For particle k over all frames:
# Count adsorption events (True → False transitions)
r_M[k] = count_transitions(inmobile_states[k], from_state=True, to_state=False)

# Collect adsorption durations
tau_S_list = []
for m in range(r_M[k]):
    duration = (i_end[m] - i_start[m]) * delta  # frames × time_per_frame
    tau_S_list.append(duration)

# Total adsorbed time
t_S[k] = sum(tau_S_list)
```

**Mathematical structure:**
- $r_M$ = random number of adsorptions
- $\{\tau_{S,1}, \tau_{S,2}, ..., \tau_{S,r_M}\}$ = random durations
- $t_S = \sum_{m=1}^{r_M} \tau_{S,m}$ = random sum

**Lévy identification:**
- This is a **compound sum** (random # of random terms)
- If $r_M \sim$ Poisson and $\tau_S \sim$ Exponential, then $t_S$ is a **Compound Poisson Process**

---

### Step 2: State the GEC Model Assumptions (Dondi 2002)

From `study/` review of Dondi 2002 paper:

**(a) Pore egress time is exponential** (Eq. 41):

$$f_p(\tau; r, d) = \frac{1}{\bar{\tau}_p(r,d)} \exp\left(-\frac{\tau}{\bar{\tau}_p(r,d)}\right)$$

**Animation check**: Does your collision mechanics produce this? (To be verified!)

**(b) Number of ingress steps is Poissonian** (Eq. 42):

$$P(r_M = n; r, d) = \frac{e^{-\bar{n}_p(r,d)} \bar{n}_p(r,d)^n}{n!}$$

**Animation check**: Does your random walk produce this? (To be verified!)

**(c) Independent events**:
- Each adsorption is independent
- Duration of mth adsorption independent of (m-1)th

**Animation**: Assumed (no memory in collision detection)

---

### Step 3: Apply Lévy-Khintchine Theorem

**For a Compound Poisson Process:**

The Lévy measure for **discrete jumps** at times $\tau_{S,i}$ with probabilities $\Delta F(\tau_{S,i})$ is:

$$\nu(d\tau) = \sum_{i} \Delta F(\tau_{S,i}) \delta(\tau - \tau_{S,i}) d\tau$$

where $\delta$ is the Dirac delta.

**For continuous jumps** (exponential case):

$$\nu(d\tau) = \lambda f(\tau) d\tau = \lambda \frac{1}{\bar{\tau}_S} e^{-\tau/\bar{\tau}_S} d\tau$$

**Lévy-Khintchine formula becomes:**

$$\psi(ω) = \int_0^∞ (e^{iω\tau} - 1) \nu(d\tau)$$

For **discrete** jumps (Pasti 2005 Eq. 26a):

$$\psi(ω) = \bar{n}_p \sum_i (e^{iω\tau_{S,i}} - 1) \Delta F(\tau_{S,i})$$

For **continuous exponential** jumps (Dondi 2002 Eq. 43):

$$\psi(ω) = \bar{n}_p \int_0^∞ (e^{iω\tau} - 1) \frac{1}{\bar{\tau}_S} e^{-\tau/\bar{\tau}_S} d\tau$$

---

### Step 4: Evaluate the Integral (Exponential Case)

**Compute:**

$$\int_0^∞ (e^{iω\tau} - 1) \frac{1}{\bar{\tau}_S} e^{-\tau/\bar{\tau}_S} d\tau$$

**Split into two parts:**

$$= \frac{1}{\bar{\tau}_S} \left[\int_0^∞ e^{iω\tau} e^{-\tau/\bar{\tau}_S} d\tau - \int_0^∞ e^{-\tau/\bar{\tau}_S} d\tau\right]$$

**First integral:**

$$\int_0^∞ e^{(iω - 1/\bar{\tau}_S)\tau} d\tau = \frac{1}{1/\bar{\tau}_S - iω} = \frac{\bar{\tau}_S}{1 - iω\bar{\tau}_S}$$

**Second integral:**

$$\int_0^∞ e^{-\tau/\bar{\tau}_S} d\tau = \bar{\tau}_S$$

**Combine:**

$$\frac{1}{\bar{\tau}_S} \left[\frac{\bar{\tau}_S}{1 - iω\bar{\tau}_S} - \bar{\tau}_S\right] = \frac{1}{1 - iω\bar{\tau}_S} - 1 = \frac{iω\bar{\tau}_S}{1 - iω\bar{\tau}_S}$$

---

### Step 5: Write the GEC Characteristic Function

**Lévy exponent:**

$$\psi(ω) = \bar{n}_p \cdot \frac{iω\bar{\tau}_S}{1 - iω\bar{\tau}_S}$$

**Characteristic function at column end ($t = t_M$):**

Using $\bar{n}_p \bar{\tau}_S = \bar{t}_S$ (mean total adsorbed time):

$$\boxed{\phi(ω) = \exp\left[\bar{n}_p \left(\frac{e^{iω\bar{\tau}_S} - 1}{1 - iω\bar{\tau}_S}\right)\right]}$$

or equivalently (Dondi 2002, Eq. 43):

$$\boxed{\phi(ω) = \exp\left[\bar{n}_p \left(\frac{1}{1 - iω\bar{\tau}_S} - 1\right)\right]}$$

**This is the monopore GEC model CF!**

---

### Step 6: Derive Moments Using Cumulants

**Lévy advantage**: Moments come from derivatives of $\psi(ω)$:

$$\kappa_n = (-i)^n \left.\frac{d^n \psi}{dω^n}\right|_{ω=0}$$

**Mean ($n=1$):**

$$\bar{t}_S = -i \psi'(0) = \bar{n}_p \bar{\tau}_S$$

**Variance ($n=2$):**

$$\text{Var}[t_S] = -\psi''(0) = \bar{n}_p \bar{\tau}_S^2 + \bar{n}_p \bar{\tau}_S^2 = 2\bar{n}_p \bar{\tau}_S^2$$

Note the **factor of 2**: One from Poisson variance, one from exponential variance (Dondi 2002, p. 193).

---

## 6. Comparison: Manual vs Lévy-Aware

### 6.1 Manual Convolution Approach

**Without Lévy awareness**, you would:

```python
# Pseudo-code for manual approach
def compute_cf_manual(omega, n_bar, tau_bar):
    """Compute CF by summing over all possible n values"""
    cf = 0 + 0j
    for n in range(0, MAX_N):  # Truncate sum at some large N
        # Poisson probability of n events
        p_n = (n_bar**n / factorial(n)) * exp(-n_bar)
        
        # CF of n-fold convolution of exponential
        # (derived separately via Laplace transform)
        cf_n = (1 / (1 - 1j*omega*tau_bar))**n
        
        cf += p_n * cf_n
    
    return cf
```

**Problems:**
- Need to truncate infinite sum
- Requires separate derivation of $n$-fold convolution
- Numerically unstable for large $n$
- Doesn't generalize easily

### 6.2 Lévy-Aware Approach

**With Lévy awareness**:

```python
def compute_cf_levy(omega, n_bar, tau_bar):
    """Direct application of CPP formula"""
    psi = n_bar * (exp(1j*omega*tau_bar) - 1) / (1 - 1j*omega*tau_bar)
    return exp(psi)
```

**Advantages:**
- One line!
- Exact (no truncation)
- Numerically stable
- Theorem guarantees correctness

---

## 7. Verification with Animation Data

### 7.1 What to Extract

To verify if your animation implements the GEC model:

```python
# Instrument the animation to collect:
adsorption_durations = []  # List of all τ_S values
adsorption_counts = []      # r_M for each particle

# For each particle k:
for k in range(num_particles):
    # Track state transitions
    durations_k = extract_adsorption_durations(inmobile_states[k, :], delta)
    adsorption_durations.extend(durations_k)
    adsorption_counts.append(len(durations_k))
```

### 7.2 Statistical Tests

**(a) Test exponential egress time:**

```python
import scipy.stats as stats

# Fit exponential distribution
tau_bar_fitted = np.mean(adsorption_durations)

# Kolmogorov-Smirnov test
ks_stat, p_value = stats.kstest(
    adsorption_durations, 
    lambda x: stats.expon.cdf(x, scale=tau_bar_fitted)
)

print(f"KS test: p-value = {p_value}")
# If p > 0.05, consistent with exponential
```

**(b) Test Poissonian ingress count:**

```python
# Fit Poisson distribution
n_bar_fitted = np.mean(adsorption_counts)

# Chi-square goodness of fit
observed_freq, bins = np.histogram(adsorption_counts, bins=range(max(adsorption_counts)+2))
expected_freq = len(adsorption_counts) * stats.poisson.pmf(bins[:-1], n_bar_fitted)

chi2, p_value = stats.chisquare(observed_freq, expected_freq)
print(f"Chi-square test: p-value = {p_value}")
```

### 7.3 Compare Empirical vs Theoretical CF

```python
# Empirical CF from simulation data
t_S_all = [sum(durations_k) for durations_k in all_particle_durations]
omega_test = np.linspace(-1, 1, 50)

cf_empirical = np.array([np.mean(np.exp(1j*w*np.array(t_S_all))) for w in omega_test])

# Theoretical CF from GEC model
cf_theoretical = compute_cf_levy(omega_test, n_bar_fitted, tau_bar_fitted)

# Plot comparison
plt.plot(omega_test, np.abs(cf_empirical), label='Empirical')
plt.plot(omega_test, np.abs(cf_theoretical), label='GEC Theory', linestyle='--')
plt.legend()
```

---

## 8. References

1. **Giddings, J.C.; Eyring, H.** (1955) "A Molecular Dynamic Theory of Chromatography", *J. Phys. Chem.*, 59, 416-421.

2. **Dondi, F.; Cavazzini, A.; Remelli, M.; Felinger, A.; Martin, M.** (2002) "Stochastic theory of size exclusion chromatography by the characteristic function approach", *J. Chromatogr. A*, 943, 185-207.
   - **Key equations**: 41 (exponential egress), 42 (Poisson ingress), 43 (GEC CF)

3. **Pasti, L.; Cavazzini, A.; Felinger, A.; Martin, M.; Dondi, F.** (2005) "Single-Molecule Observation and Chromatography Unified by Lévy Process Representation", *Anal. Chem.*, 77, 2524-2535.
   - **Key equations**: 26a (discrete jumps), 26b (NS+S model)

4. **Sato, K.** (1999) *Lévy Processes and Infinitely Divisible Distributions*, Cambridge University Press.
   - Standard reference for Lévy-Khintchine theorem

5. **Applebaum, D.** (2009) *Lévy Processes and Stochastic Calculus*, 2nd ed., Cambridge University Press.
   - Compound Poisson processes, Lévy-Itô decomposition

---

## Appendix A: Animation Code References

### Key variables in `ColumnSimulation.py`:

```python
# Particle state tracking
inmobile_states[k]     # True = mobile, False = adsorbed
grain_references[k]    # -1 = mobile, j = grain index

# Position tracking
pyv[k]                 # y-position at current frame
pxv[k]                 # x-position at current frame

# Species identification
ptype_indeces[k]       # 0 = large, 1 = medium, 2 = small
large_indeces          # Indices of large particles
middle_indeces         # Indices of medium particles
small_indeces          # Indices of small particles

# Chromatographic output
x_hist_large[i]        # # of large particles at y≈0 at frame i
x_hist_middle[i]       # # of medium particles at y≈0 at frame i
x_hist_small[i]        # # of small particles at y≈0 at frame i
```

### Functions to instrument for data collection:

- `touchable_indeces()`: Detects adsorption events (True → False)
- `compute_next_positions()`: Updates particle states each frame
- `particle.stationary_move()`: Models adsorbed particle behavior

---

## Appendix B: Glossary

| **Term** | **Definition** | **Animation Equivalent** |
|----------|---------------|-------------------------|
| Lévy process | Stochastic process with independent, stationary increments | Particle's cumulative adsorption time $t_S(t)$ |
| Compound Poisson Process (CPP) | Lévy process with only jump component | GEC model ($r_M$ Poisson jumps) |
| Lévy measure $\nu(dx)$ | Distribution of jump sizes | Distribution of $\tau_S$ values |
| Characteristic function | Fourier transform of probability distribution | $\phi(ω) = E[e^{iω t_S}]$ |
| Lévy-Khintchine representation | Canonical form of Lévy process CF | $\phi(ω,t) = \exp[t\psi(ω)]$ |
| Cumulant | Coefficient in log-CF Taylor expansion | Moments without convolution |
| Realization | One sample path from process | `pyv[k, :]` for particle k |
| Ensemble | Collection of all realizations | All 1500 particles |

---

**End of Document**

© 2025 Molass Community, CC BY 4.0
