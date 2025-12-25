# Proof of the Characteristic Function for the GEC Model

**Reference:** Dondi, F., Blo, G., Remelli, M., & Reschiglian, P. (1992). "Stochastic Theory of Chromatography: The Characteristic Function Method and the Approximation of Chromatographic Peak Shape." In *Theoretical Advancement in Chromatography and Related Separation Techniques*, NATO ASI Series C, Vol. 383, Kluwer Academic, Dordrecht, pp. 173-210.

**Applied in:** Dondi, F., Cavazzini, A., Remelli, M., & Felinger, A. (2002). "Stochastic theory of size exclusion chromatography by the characteristic function approach." *Journal of Chromatography A*, 943, 185-207.

---

## Overview

This document summarizes how the characteristic function (CF) for the Giddings-Eyring-Carmichael (GEC) model is proved in the 1992 Dondi et al. paper. The GEC model assumes:
- **Poisson-distributed** pore entry process
- **Exponentially-distributed** pore residence time

The final result (Eq. 43 in the 2002 paper) is:

$$\phi_{t_p}(\xi; r, d) = \exp\left[\bar{n}_p(r,d)\left(\frac{1}{1 - i\xi\bar{t}_p(r,d)} - 1\right)\right]$$

---

## Step 1: General Mixture Process (Section 5.1)

### The Chromatographic Model

In the **constant mobile phase velocity model**:
- A molecule performs **n sorption steps** (random integer variable)
- Each step has **sorption time Δt_s** (random continuous variable)
- The total sorption time is a **compound/mixture process**

### Total Sorption Time Distribution

The frequency function of total sorption time is (Eq. 43a):

$$f_{s,tot}(t_s) = \sum_n p_n f_s^{*n}(t_s)$$

where:
- $p_n$ = probability of exactly n sorption entries
- $f_s^{*n}$ = n-fold convolution of single sorption time distribution
- The sum represents a mixture of processes

### Characteristic Function Form

The CF of this mixture process is (Eq. 43b):

$$\phi_{s,tot}(\xi) = \sum_n p_n [\phi_s(\xi)]^n$$

where:
- $\phi_s(\xi)$ = CF of single sorption time
- The power n represents the n-fold convolution property

**Key observation:** This equation holds for **ANY** distribution of entry numbers and **ANY** distribution of sorption times.

---

## Step 2: Log-Exp Transformation (The Key Trick!)

### Mathematical Identity

Using the identity $x^r = \exp[r \ln(x)]$ (Eq. 45), rewrite Eq. 43b as:

$$\phi_{s,tot}(\xi) = \sum_n p_n \exp\left[n \cdot \frac{\ln(\phi_s(\xi))}{i} \cdot i\right]$$

This is Eq. 46a in the 1992 paper.

### Why This Works

The imaginary unit $i$ is introduced to maintain dimensional consistency:
- $\ln(\phi_s(\xi))$ is generally a complex number
- Dividing by $i$ and multiplying by $i$ allows proper interpretation as an auxiliary variable

---

## Step 3: Recognition of CF Form (Brilliant Insight!)

### Pattern Recognition

The right-hand side of Eq. 46a has the form:

$$\sum_n p_n \exp\left[i \cdot \left(\frac{\ln(\phi_s(\xi))}{i}\right) \cdot n\right]$$

This is **exactly the definition** of the characteristic function of the discrete random variable n (Eq. 20b, 44):

$$\phi_n(\xi) = \sum_n p_n e^{i\xi n}$$

but with the auxiliary variable **replaced** by the complex function:

$$\xi \rightarrow \frac{\ln(\phi_s(\xi))}{i}$$

### General Solution

By this recognition, the **general solution** is (Eq. 46b):

$$\phi_{s,tot}(\xi) = \phi_{n,tot}\left[\frac{\ln(\phi_s(\xi))}{i}\right]$$

Or equivalently, in 2nd CF (cumulant generating function) form (Eq. 46c):

$$\psi_{s,tot}(\xi) = \psi_{n,tot}\left[\frac{\psi_s(\xi)}{i}\right]$$

where $\psi(\xi) = \ln(\phi(\xi))$ is the second characteristic function.

### Universality

This result is **completely general**:
- No assumption about the form of $p_n$ (entry distribution)
- No assumption about the form of $f_s$ (sorption time distribution)
- Works for any compound/mixture stochastic process

---

## Step 4: Specialization to Poisson Entry Process (Section 5.3)

### Poisson Distribution

For a **Poisson entry process** (arising from exponential waiting time between entries), the CF is (Eq. 51c):

$$\phi_{n,tot}(\xi) = \exp\{\bar{n}[\exp(i\xi) - 1]\}$$

where $\bar{n}$ is the mean number of entries.

### Substitution

**Substitute** $\xi \to \ln(\phi_s(\xi))/i$ into the Poisson CF:

$$\phi_{s,tot}(\xi) = \exp\left\{\bar{n}\left[\exp\left(\frac{\ln(\phi_s(\xi))}{i} \cdot i\right) - 1\right]\right\}$$

### Simplification

Since $\exp(\ln(x)) = x$:

$$\phi_{s,tot}(\xi) = \exp\{\bar{n}[\phi_s(\xi) - 1]\}$$

This is **Eq. 52a** in the 1992 paper.

**At this point:** We have the CF for **Poisson entries + general sorption time**. No assumption yet about the sorption time distribution.

---

## Step 5: Adding Exponential Sorption Time

### Exponential Distribution

For **exponential sorption time** with frequency function:

$$f(\Delta t_s) = k_s \exp(-k_s \Delta t_s)$$

The CF of the exponential distribution is:

$$\phi_s(\xi) = \frac{1}{1 - i\xi/k_s}$$

or equivalently:

$$\phi_s(\xi) = \frac{1}{1 - i\xi\bar{t}_p}$$

where $\bar{t}_p = 1/k_s$ is the mean sorption time.

### Final Substitution

**Substitute** the exponential CF into Eq. 52a:

$$\phi_{s,tot}(\xi) = \exp\left\{\bar{n}\left[\frac{1}{1 - i\xi\bar{t}_p} - 1\right]\right\}$$

### Result

This is **exactly Equation 43** from the 2002 Dondi et al. paper on SEC!

For the SEC application with size dependence:

$$\phi_{t_p}(\xi; r, d) = \exp\left[\bar{n}_p(r,d)\left(\frac{1}{1 - i\xi\bar{t}_p(r,d)} - 1\right]\right]$$

where:
- $r$ = molecule size parameter
- $d$ = pore size
- $\bar{n}_p(r,d)$ = mean number of pore entries (size-dependent)
- $\bar{t}_p(r,d)$ = mean time per pore visit (size-dependent)

---

## Mathematical Insight and Significance

### The Brilliance of This Proof

1. **Recognizing the structure:** A compound/mixture process (sum of random number of random variables) can be solved elegantly using log-exp transformation

2. **Variable substitution trick:** After transformation, the result is simply the CF of the entry number distribution with a **transformed auxiliary variable** $\ln(\phi_s(\xi))/i$

3. **Universality:** This framework works for **ANY** combination of:
   - Entry process distribution (Poisson, Geometric, Negative Binomial, etc.)
   - Sorption time distribution (Exponential, Gamma, Log-normal, etc.)

4. **Computational power:** The GEC model produces a remarkably simple **closed-form expression** because both processes are exponential

### Physical Interpretation

The CF structure $\exp\{\bar{n}[\phi_s - 1]\}$ reveals:

- **$\bar{n}$:** Controls the number of random sorption events (stochastic complexity)
- **$\phi_s - 1$:** Represents the "deviation from certainty" for each event
- The product shows how stochastic complexity compounds through multiple random events

### Extensions

The 1992 paper shows this framework extends to:
- **Non-constant mobile phase velocity** (including diffusion effects)
- **Heterogeneous stationary phases** (mixed retention mechanisms)
- **Continuous pore size distributions** (polydisperse materials)

All by maintaining the same log-exp transformation principle.

---

## Summary of the Proof Chain

```
General Mixture Process (Eq. 43b)
    ↓ (Log-exp transformation)
Recognition of CF structure (Eq. 46a)
    ↓ (Auxiliary variable substitution)
General Solution (Eq. 46b-c)
    ↓ (Specialize to Poisson)
Poisson + General Sorption (Eq. 52a)
    ↓ (Specialize to Exponential)
GEC Model CF (Eq. 43 in 2002 paper)
```

**Key Equation Chain:**

$$\phi_{s,tot}(\xi) = \sum_n p_n [\phi_s(\xi)]^n$$
$$\downarrow$$
$$\phi_{s,tot}(\xi) = \phi_{n,tot}\left[\frac{\ln(\phi_s(\xi))}{i}\right]$$
$$\downarrow$$
$$\phi_{s,tot}(\xi) = \exp\{\bar{n}[\phi_s(\xi) - 1]\}$$
$$\downarrow$$
$$\phi_{s,tot}(\xi) = \exp\left\{\bar{n}\left[\frac{1}{1 - i\xi\bar{t}_p} - 1\right]\right\}$$

---

## References

1. Dondi, F., Blo, G., Remelli, M., & Reschiglian, P. (1992). In *Theoretical Advancement in Chromatography*, NATO ASI Series C, Vol. 383, pp. 173-210.

2. Dondi, F., Cavazzini, A., Remelli, M., & Felinger, A. (2002). *Journal of Chromatography A*, 943, 185-207.

3. Giddings, J.C., & Eyring, H. (1955). *Journal of Physical Chemistry*, 59, 416.

4. McQuarrie, D.A. (1963). *Journal of Chemical Physics*, 38, 437.

---

**Document created:** December 17, 2025  
**Summary of:** 1992 Dondi et al. proof methodology for GEC model characteristic function
