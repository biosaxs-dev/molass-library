# Mathematical Proof: Y(t) = Spatial Position is NOT a Lévy Process

## Definitions

A **Lévy process** {X(t), t ≥ 0} must satisfy:

1. **X(0) = 0** (starts at origin)
2. **Independent increments**: For any 0 ≤ t₀ < t₁ < t₂ < t₃, the increments X(t₂) - X(t₁) and X(t₃) - X(t₂) are independent random variables
3. **Stationary increments**: For any s, t ≥ 0, X(t+s) - X(s) has the same distribution as X(t) - X(0)
4. **Stochastic continuity**: For any ε > 0 and t ≥ 0, lim_{h→0} P(|X(t+h) - X(t)| > ε) = 0

## Why Y(t) = Spatial Position Fails

### Failure 1: NOT Independent Increments

**Setup:**
- Let Y(t) = vertical position of particle at time t
- Let S(t) ∈ {mobile, adsorbed} be the hidden state

**Key observation:** The particle's motion depends on state S(t):
- If S(t) = mobile: Y(t+1) - Y(t) ~ N(μ_mobile, σ²_mobile) (diffusion + drift)
- If S(t) = adsorbed: Y(t+1) - Y(t) = 0 (no movement)

**Proof of dependence:**

Consider two consecutive increments:
- ΔY₁ = Y(t₁) - Y(t₀) 
- ΔY₂ = Y(t₂) - Y(t₁)

**Case 1:** If ΔY₁ = 0, this suggests S(t₀) through S(t₁) was likely adsorbed.

Since the state process S(t) is a Markov chain with persistence (particle tends to stay in same state for multiple frames), if S(t₁) = adsorbed, then P(S(t₂) = adsorbed | S(t₁) = adsorbed) > P(S(t₂) = adsorbed) (prior).

Therefore:
```
P(ΔY₂ = 0 | ΔY₁ = 0) > P(ΔY₂ = 0)
```

This means **ΔY₂ is NOT independent of ΔY₁**! ❌

### Failure 2: NOT Stationary Increments

**Proof:** The increment distribution Y(t+h) - Y(t) changes based on:

1. **Position-dependent packing:**
   - Near top: less porous medium, more mobile phase
   - In column: dense porous particles
   - Distribution changes with Y(t)!

2. **Systematic drift:**
   - Particle flows downward with mean velocity v_drift
   - E[Y(t+h) - Y(t)] = v_drift · h + corrections
   - This is a **NON-ZERO drift** that persists throughout

3. **Boundary effects:**
   - Y(t) is bounded: 0 ≤ Y(t) ≤ L_column
   - Near boundaries, distribution must change
   - Y(t+h) - Y(t) distribution depends on Y(t)!

**Formal counterexample:**
- At t=0 (top of column): E[Y(h) - Y(0)] includes drift + minimal adsorption
- At t=T (deep in column): E[Y(T+h) - Y(T)] includes drift + significant adsorption

Since E[Y(h) - Y(0)] ≠ E[Y(T+h) - Y(T)], the increments are **NOT stationary**! ❌

## Why t_S(t) = Cumulative Adsorbed Time IS a Lévy Process (CPP)

### Independent Increments ✓

**Setup:** Let N(t) = number of adsorption events up to time t (Poisson process with rate λ).

The increment t_S(t₂) - t_S(t₁) = sum of jump sizes τᵢ that occur during (t₁, t₂].

**Key property:**
- Jump sizes τᵢ ~ F(τ) are i.i.d.
- Number of jumps in (t₁, t₂] depends only on the interval length (t₂ - t₁), not on past
- Poisson process has independent increments

Therefore: t_S(t₂) - t_S(t₁) is independent of t_S(t₁) - t_S(t₀) ✓

### Stationary Increments ✓

**Proof:**
For any s, t ≥ 0:
- t_S(t+s) - t_S(s) = sum of τᵢ that arrive during (s, t+s]
- Expected number of arrivals = λ·t (depends only on interval length!)
- Each τᵢ ~ F(τ) (same distribution throughout time)

Distribution of t_S(t+s) - t_S(s):
```
ℙ(t_S(t+s) - t_S(s) ≤ x) = Σ_{k=0}^∞ ℙ(N(t) = k) · ℙ(τ₁ + ... + τₖ ≤ x)
                         = Σ_{k=0}^∞ (λt)^k/k! e^{-λt} · F^{*k}(x)
```

This depends only on t, not on s! Therefore **stationary increments** ✓

## Summary

| Property | Y(t) = Position | t_S(t) = Adsorbed Time |
|----------|----------------|----------------------|
| Independent increments | ❌ No (state dependence) | ✓ Yes (CPP structure) |
| Stationary increments | ❌ No (drift, boundaries) | ✓ Yes (constant λ, F) |
| **Is Lévy Process?** | **❌ NO** | **✓ YES (CPP)** |

## References

- **Lévy Processes**: Bertoin, J. (1996). "Lévy Processes." Cambridge University Press.
- **CPP in Chromatography**: Pasti et al. (2005). "Single-Molecule Observation and Chromatography Unified by Lévy Process Representation." Analytical Chemistry, 77(8), 2524-2535.
- **Markov Chains**: The hidden state process S(t) is Markovian, but Y(t) conditioned on S(t) still fails independence due to state persistence.

## Empirical Test

Run `test_position_independence.py` to see:
- Correlation between consecutive increments ΔY[t] and ΔY[t+1] >> 0
- State-dependent increment distributions
- Changing mean and variance across trajectory chunks

**Result:** Empirical data confirms Y(t) is NOT a Lévy process!
