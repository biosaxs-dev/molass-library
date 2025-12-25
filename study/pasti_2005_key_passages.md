# Key Passages from Pasti 2005: What IS the Lévy Process?

## Critical Quote (Page 2, Line 114):

> "The Poisson law of eqs 2a-d can be viewed as a 'process', i.e., as a random sequence of adsorption events during the progressing time t_m:"
>
> **"related to the variable position l (0 ≤ l ≤ L) inside the column."**

## Interpretation:

### What Pasti 2005 Says:

1. **The stochastic process** = "random sequence of adsorption events during the progressing time t_m"
   - This is t_s(t_m), the cumulative adsorbed time
   - This is the random variable

2. **Position l is NOT the stochastic process** = "variable position l"
   - Called a "variable" not a "random variable"
   - It's a **parameter** that relates to where you are in the column
   - Used via equation (3): t_m = l/u_M (deterministic relationship!)

### Key Terminology Distinctions in the Paper:

| Term | What Pasti Calls It | What It Is |
|------|-------------------|-----------|
| **t_s, t_S** | "random variable" (line 127) | **THE Lévy process** ✓ |
| **τ_S (jump sizes)** | "random variable" (line 107) | i.i.d. components of CPP ✓ |
| **r_m (# events)** | "number (random)" (line 118) | Poisson random variable ✓ |
| **l (position)** | "variable position" (line 114) | **Parameter, NOT random** |
| **t_m (mobile time)** | "time" (deterministic) | Deterministic clock = l/u_M |

## Explicit Confirmation (Page 3, Lines 175-182):

> "In this case, the random variable will not be r_m but r_m·ô_S..."
>
> "In a real chromatographic process, the time spent in the adsorbed state, ô_S, is **a random quantity**."

They explicitly call **TIME** variables random, never call position random.

## Glossary Confirmation (Page 12):

| Symbol | Definition |
|--------|-----------|
| **t_s** | "time spent in the stationary phase up to the position l in the column" |
| **t_S** | "time spent in the stationary phase up to the column end" |
| **l** | "intermediate position in the column (0 < l < L)" |
| **L** | "column length" |

Note: **l and L are geometric parameters**, while **t_s and t_S are stochastic processes**.

## The Lévy-Khintchine Formula (Page 4, Equation 9):

```
Φ_{ô_S,C}(t_s; ω | t_m) = exp{t_m ∫[e^(iωô_S) - 1] M(dô_S)}
```

- Integration over **ô_S** (TIME durations), not position!
- Lévy measure **M(dô_S)** describes distribution of TIME jumps
- The process is indexed by **t_m** (mobile phase time)

## Answer to Your Question:

**Yes, Pasti 2005 DOES note this implicitly**, though not as explicitly as we stated it.

They make it clear by:
1. ✓ Calling position l a "variable" (parameter), never "random variable"
2. ✓ Building entire Lévy framework on TIME variables (t_s, ô_S, τ)
3. ✓ Using equation t_m = l/u_M to show position is deterministically related to time
4. ✓ Only defining characteristic functions for TIME-based random variables
5. ✓ Glossary distinguishes geometric parameters (l, L) from stochastic processes (t_s, t_S)

**What they DON'T do:**
- ❌ They don't explicitly state "spatial position is NOT a Lévy process"
- ❌ They don't explain WHY position can't be a Lévy process
- ❌ They assume readers understand this from context

This is typical in mathematical physics papers - they focus on what the model IS, not what it ISN'T. Our explicit proof fills this pedagogical gap!

## Why This Matters for SDM:

In stochastic differential multiplier (SDM) models:
- **t_R = t_M + t_S** (retention time = mobile + stationary time)
- **t_S is the Lévy process** (CPP with Poisson arrivals and exponential jump sizes)
- **Position flows deterministically** once you know the velocity profile and time

The randomness is in HOW LONG particles stay stuck, not in WHERE they go spatially!
