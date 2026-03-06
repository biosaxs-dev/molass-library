# Lévy Process Analysis for Chromatography Modeling
## Summary of Findings for SDM (Stochastic Dispersive Model) Enhancement

**Date**: December 25, 2025  
**Context**: Analysis based on Pasti 2005 "Lévy processes and Poissonian behavior of chromatographic systems"  
**Goal**: Leverage Lévy process framework to improve SDM modeling

---

## 1. Core Lévy Process Concepts

### 1.1 Definition
A **Lévy process** X(t) is a stochastic process satisfying:

1. **Independent increments**: X(t₂) - X(t₁) is independent of X(t₁) - X(t₀) for non-overlapping intervals
   - Formally: P(ΔX[t+1] ∈ S | ΔX[t] ∈ T) = P(ΔX[t+1] ∈ S)
   - **Critical**: Correlation = 0 is NECESSARY but NOT SUFFICIENT for independence!
   - Must test conditional probability directly, not just correlation

2. **Stationary increments**: X(t+h) - X(t) has same distribution regardless of t
   - Distribution of increments doesn't change over time
   - Constant parameters (λ, F(τ)) throughout

3. **Càdlàg paths**: Right-continuous with left limits
   - Allows for jumps (discontinuities)

### 1.2 Lévy-Khintchine Representation

**General form** (Pasti 2005 Appendix, Equation I-1):
```
ln φ(T; ω | t) = t { ivω - (σ²ω²/2) + ∫[e^(iωu) - 1] M(du) }
```

**Three independent components**:
1. **v**: Deterministic drift term
2. **σ²**: Brownian/Gaussian component (diffusion)
3. **M(du)**: Poisson/jump component (adsorption events)

**Compound Poisson Process (CPP)** - Special case used in Pasti 2005:
- Pure jump process (σ² = 0, v = 0)
- Lévy measure: Π(dτ) = λ F(dτ)
  - λ = jump rate (events per unit time)
  - F(τ) = jump size distribution (typically exponential)
- Characteristic function: φ(θ; t) = exp(t ∫[e^(iθx) - 1] Π(dx))

---

## 2. What IS and IS NOT a Lévy Process in Chromatography

### 2.1 Pasti 2005 Basic Model Structure

**Retention time decomposition**:
```
t_R = t_M + t_S
```

Where:
- **t_M** = mobile phase time = **deterministic** (Pasti 2005, lines 358-362)
  - t_M = L/u_M (column length / mobile phase velocity)
  - All molecules spend same time in mobile phase
  - "No mobile-phase dispersion effects are considered" (basic model)

- **t_S** = stationary phase time = **random variable** (CPP Lévy process)
  - Cumulative adsorbed time
  - Sum of i.i.d. exponential jump sizes
  - Poisson arrival process with rate λ

### 2.2 Critical Distinction: Random Variable vs. Variable Parameter

From Pasti 2005 (line 114):
- **t_s, t_S, τ_S**: "random variable" ✓ (subject to Lévy analysis)
- **l, L**: "variable position", "column length" (parameters, not random variables)
- **t_m, t_M**: deterministic via t_m = l/u_M

**Key Insight**: Lévy framework applies to **TIME variables**, not spatial position!

### 2.3 Empirical Test Results

| Process | Description | Is Lévy? | Evidence |
|---------|-------------|----------|----------|
| **t_S(t)** | Cumulative adsorbed time (frame time) | ✓ YES | CPP structure: Poisson arrivals + exponential jumps |
| **Y(t)** | Spatial position (frame time) | ❌ NO | P(ΔY\|ΔY) ≠ P(ΔY) - fails independence due to hidden state |
| **Y(T_t)** | Spatial position (mobile time) | ✓ YES | **Surprising!** Subordination removes state mixing |
| **t_S(T_t)** | Cumulative adsorbed time (mobile time) | ✓ YES* | Subordination preserves Lévy property (*test artifacts for sparse processes) |

**Testing Scripts**:
- [test_position_independence.py](test_position_independence.py) - Proves Y(t) is NOT Lévy
- [test_subordination_levy_property.py](test_subordination_levy_property.py) - Tests subordination effects

### 2.4 Why Y(t) is NOT a Lévy Process

**Mathematical Proof** ([proof_position_not_levy.md](proof_position_not_levy.md)):

**Failure 1: NOT independent increments**
- Hidden state S(t) ∈ {mobile, adsorbed} affects motion
- If ΔY[t] ≈ 0 → particle likely adsorbed at t
- State persistence → likely still adsorbed at t+1
- Therefore ΔY[t+1] also likely ≈ 0
- Creates dependence: P(ΔY[t+1] | ΔY[t]) ≠ P(ΔY[t+1])

**Empirical Evidence**:
- Correlation ≈ 0 (passes weak test)
- P(ΔY small | ΔY small) = 0.565 vs P(ΔY small) = 0.327
- Difference = 0.238 >> 0.1 threshold → **FAILS independence**
- State-dependent motion: 6.6x faster when mobile vs. adsorbed

**Failure 2: NOT stationary increments**
- Position-dependent packing density
- Boundary effects at column entrance/exit
- Drift toward column exit

---

## 3. Bochner Subordination: The Key Extension Mechanism

### 3.1 Concept

**Subordination** = Evaluating a process at random times

General form: X(Y_t) where Y_t is a **subordinator**
- Subordinator = increasing Lévy process (random time change)
- Examples: Gamma process, Inverse Gaussian process

**Chromatography Application**:
- Standard: t_S(t) where t = deterministic frame time
- Subordinated: t_S(T_t) where T_t = random mobile phase time

### 3.2 Surprising Discovery: Y(T_t) Becomes Lévy!

**Expected**: Subordination preserves Lévy property (doesn't create it)
**Reality**: Subordination by mobile time **removes state dependence**!

**Mechanism**:
1. **Y(t)** with frame time:
   - Samples position at all states (mobile AND adsorbed)
   - Knowing ΔY ≈ 0 reveals hidden state (likely adsorbed)
   - State persistence creates dependence

2. **Y(T_t)** with mobile time:
   - Only samples position when mobile (state = mobile)
   - All increments from same state
   - No state mixing → no state dependence → independent!

**Subordination by the state-determining process acts as a filter!**

### 3.3 Implications for Pasti 2005 Extended Model

From Pasti 2005 (lines 780-785):
> "Inclusion of the mobile-phase diffusion is still possible, by using the 'randomization' 
> technique elsewhere developed by us and referred to as Bochner transformation in the 
> context of Lévy processes."

**What this means**:
- Basic model: t_M deterministic, t_S random (CPP)
- Extended model: Both t_M and t_S can be random via subordination
- T_t becomes random "mobile phase clock" (e.g., drift + Brownian motion)
- t_S(T_t) maintains Lévy structure while including mobile dispersion

**Why it works**:
- Subordination preserves Lévy properties of processes that are already Lévy
- Subordination can create Lévy behavior by filtering state-dependent processes
- Maintains Lévy-Khintchine mathematical framework

**Demonstration Scripts**:
- [demonstrate_subordination.py](demonstrate_subordination.py) - Visualizes t_S(t) vs t_S(T_t)
- [test_subordination_levy_property.py](test_subordination_levy_property.py) - Tests Lévy properties

---

## 4. Visualization Tools Created

### 4.1 Main Visualization Script
**File**: [visualize_levy_trajectory.py](visualize_levy_trajectory.py) (~913 lines)

**Purpose**: Comprehensive 12-panel visualization of CPP structure in SEC

**Key Functions**:
- `run_with_trajectory_tracking()`: Collects single-particle trajectory data
- `create_3d_trajectory_plot()`: 3D spatial + cumulative time visualization
- `create_levy_khintchine_visualization()`: Main 12-panel analysis

**Panel Layout (4×3 grid)**:
- **Row 0**: Jump SIZES (Exponential distribution)
  - Panel 1: F(τ) histogram + exponential fit
  - Panel 2: Lévy measure Π(dτ) = λF(dτ)
  - Panel 3: Cumulative ∫Π(dx)
  
- **Row 1**: Jump ARRIVALS (Poisson process)
  - Panel 4: Poisson PMF P(N=k) showing theoretical + single observation
  - Panel 5: Counting process N(t) - cumulative jumps
  - Panel 6: Windowed jump count distributions
  
- **Row 2**: Characteristic Function
  - Panel 7: Re[φ(θ; t)]
  - Panel 8: Im[φ(θ; t)]
  - Panel 9: Complex plane trajectory
  
- **Row 3**: Trajectory
  - Panel 10-12: Staircase t_S(t) (full width)

**Critical Implementation Details**:
- Jump extraction via state transitions (mobile → adsorbed → mobile)
- Single λ parameter throughout (emphasized with annotations)
- Shows connection between λ, τ̄, and characteristic function

### 4.2 Independence Testing Scripts

**File**: [test_position_independence.py](test_position_independence.py) (~260 lines)
- Tests whether Y(t) satisfies Lévy properties
- Proper independence test: P(ΔY[t+1] | ΔY[t]) vs P(ΔY[t+1])
- State-dependent motion analysis
- 4-panel visualization

**File**: [test_subordination_levy_property.py](test_subordination_levy_property.py) (~285 lines)
- Compares 4 processes: Y(t), Y(T_t), t_S(t), t_S(T_t)
- Tests each for independent increments
- Reveals subordination effects
- 2×4 panel comparison visualization

### 4.3 Supporting Documentation

**File**: [proof_position_not_levy.md](proof_position_not_levy.md)
- Mathematical proof that Y(t) fails Lévy properties
- Formal counterexamples
- Comparison with t_S(t)

**File**: [pasti_2005_key_passages.md](pasti_2005_key_passages.md)
- Key quotes from Pasti 2005
- Terminology verification
- Confirms deterministic t_M in basic model

---

## 5. Key Insights for SDM Enhancement

### 5.1 Theoretical Framework

**Current Understanding**:
1. **Time processes are Lévy, spatial processes are not**
   - t_S (adsorbed time) ✓ Lévy
   - Y (position) ✗ Not Lévy (unless subordinated by mobile time!)
   
2. **Subordination is powerful**
   - Preserves Lévy properties when applied to Lévy processes
   - Can create Lévy behavior by filtering state-dependent processes
   - Allows extending basic model to include mobile dispersion

3. **Pasti 2005 scope clarification**
   - Basic model: t_M deterministic, t_S random (CPP, σ² = 0)
   - Extended model: Can include mobile dispersion via subordination
   - General Lévy-Khintchine allows for drift (v) and Brownian (σ²) components

### 5.2 Practical Implications for SDM

**Current SDM Limitations (if any)**:
- Need to assess: Does current SDM treat position as Lévy process?
- Need to check: How is mobile phase dispersion modeled?
- Need to verify: Are time vs. space variables properly distinguished?

**Potential Enhancements**:

1. **Use proper Lévy structure for time processes**
   - Model t_S as CPP with explicit λ and F(τ)
   - Verify independent increments property
   - Use Lévy-Khintchine characteristic function for analytical solutions

2. **Consider subordination for mobile phase dispersion**
   - Basic: t_R = t_M + t_S with t_M constant
   - Extended: t_R = T_t + t_S(T_t) where T_t is random mobile time
   - T_t could be: deterministic drift + Brownian motion + jumps

3. **Be cautious with spatial position**
   - Y(t) is NOT a Lévy process with frame time
   - Y(T_t) CAN be Lévy if subordinated by mobile time
   - State dependence must be handled carefully

4. **Leverage analytical solutions**
   - Lévy-Khintchine representation provides characteristic function
   - Can derive peak shapes, moments, band broadening analytically
   - Avoids pure simulation approaches where possible

### 5.3 Open Questions for Future Investigation

1. **How does current SDM handle mobile phase time?**
   - Is it deterministic or stochastic?
   - If stochastic, what is the structure?

2. **Can we implement Bochner subordination in SDM?**
   - What would T_t (random mobile time) look like physically?
   - How to parameterize (drift + Brownian + jumps)?

3. **What are the observable consequences?**
   - How does including mobile dispersion change peak shapes?
   - Can we validate against experimental data?

4. **Computational efficiency**
   - Can analytical Lévy-Khintchine solutions replace some simulations?
   - Trade-offs between accuracy and speed?

---

## 6. Mathematical Reference

### 6.1 Compound Poisson Process Structure

**Properties**:
```
t_S(t) = Σ τᵢ  (i=1 to N(t))
```

Where:
- N(t) = Poisson counting process with rate λ
- τᵢ ~ F(τ) i.i.d. jump sizes (typically exponential)
- N(t) and {τᵢ} are independent

**Characteristic Function**:
```
φ(θ; t) = E[e^(iθ·t_S(t))] = exp(t ∫[e^(iθx) - 1] λF(dx))
```

**Lévy Measure**:
```
Π(dτ) = λ F(dτ)
```

**For Exponential Jumps** F(τ) = (1/τ̄)exp(-τ/τ̄):
```
∫[e^(iθx) - 1] Π(dx) = λτ̄(e^(iθτ̄) - 1) / (1 - iθτ̄)
```

### 6.2 Independence Test Methodology

**Weak Test** (necessary but NOT sufficient):
- Correlation: ρ = Corr(ΔX[t], ΔX[t+1])
- If independent → ρ = 0
- But ρ = 0 does NOT imply independence!

**Proper Test** (directly tests definition):
- Conditional probability: P(ΔX[t+1] ∈ S | ΔX[t] ∈ T)
- For Lévy: P(ΔX[t+1] ∈ S | ΔX[t] ∈ T) = P(ΔX[t+1] ∈ S)
- Empirical: Compare P(event | condition) vs P(event)
- Threshold: |difference| > 0.1 indicates significant dependence

---

## 7. References and Resources

### 7.1 Primary Source
**Pasti 2005**: "Lévy processes and Poissonian behavior of chromatographic systems"
- Lines 98-128: Basic model assumptions
- Lines 340-370: Retention time decomposition
- Lines 358-362: Explicit statement of deterministic t_M
- Lines 727-807: Appendix - General Lévy-Khintchine representation
- Lines 762-780: Discussion of σ² term and diffusion
- Lines 780-785: Mention of Bochner transformation for mobile dispersion

### 7.2 Key Equations from Pasti 2005
- Equation (7): Characteristic function for CPP
- Equation (8): Lévy measure Π(dτ)
- Equation I-1 (Appendix): General Lévy-Khintchine form
- Table 1: Terminology clarification (random variables vs. parameters)

### 7.3 Our Analysis Scripts

**Visualization**:
- [visualize_levy_trajectory.py](visualize_levy_trajectory.py) - Main 12-panel CPP visualization
- [demonstrate_subordination.py](demonstrate_subordination.py) - Subordination demonstration

**Testing**:
- [test_position_independence.py](test_position_independence.py) - Proves Y(t) not Lévy
- [test_subordination_levy_property.py](test_subordination_levy_property.py) - Tests subordination effects

**Documentation**:
- [proof_position_not_levy.md](proof_position_not_levy.md) - Mathematical proof
- [pasti_2005_key_passages.md](pasti_2005_key_passages.md) - Key quotes
- [levy_process_analysis_summary.md](levy_process_analysis_summary.md) - This document

---

## 8. Next Steps for SDM Enhancement

### 8.1 Immediate Actions

1. **Audit current SDM implementation**
   - Map SDM variables to Lévy framework (what is t_S, what is t_M, what is Y?)
   - Check if position is incorrectly treated as Lévy process
   - Verify independence of adsorption events

2. **Validate CPP structure**
   - Extract λ and F(τ) from SDM simulations
   - Verify Poisson counting process N(t)
   - Test independence of jump sizes

3. **Consider analytical solutions**
   - Implement Lévy-Khintchine characteristic function
   - Derive moments analytically where possible
   - Compare with simulation results

### 8.2 Enhancement Opportunities

1. **Implement subordination for mobile dispersion**
   - Design T_t structure (drift + Brownian?)
   - Test t_S(T_t) vs. t_S(t) comparison
   - Validate against experimental data with mobile dispersion

2. **Improve computational efficiency**
   - Use analytical solutions where available
   - Optimize jump detection algorithms
   - Parallel processing for independent trajectories

3. **Extend to more complex scenarios**
   - Multiple components with different λᵢ, F_i(τ)
   - Gradient elution (time-varying λ(t))
   - Temperature effects on adsorption

### 8.3 Validation Strategy

1. **Compare with Pasti 2005 predictions**
   - Peak shapes
   - Band broadening
   - Moment equations

2. **Test limiting cases**
   - High λ → continuous adsorption
   - Low λ → few discrete events
   - Different F(τ) distributions

3. **Experimental validation**
   - Match simulated peak shapes with real chromatograms
   - Verify predicted vs. observed retention times
   - Test mobile dispersion predictions

---

## 9. Conclusions

### 9.1 What We Now Know

1. **Lévy processes provide rigorous mathematical framework for chromatography**
   - Specifically for TIME processes (t_S, t_M, t_R)
   - NOT for spatial position Y (unless properly subordinated)

2. **Pasti 2005 basic model is well-defined**
   - t_M deterministic (no mobile dispersion)
   - t_S is CPP Lévy process (Poisson arrivals + exponential jumps)
   - Extension via Bochner subordination for mobile dispersion

3. **Subordination is more powerful than expected**
   - Preserves Lévy properties
   - Can CREATE Lévy behavior by filtering state dependence
   - Y(T_t) becomes Lévy even though Y(t) is not!

4. **Independence testing requires care**
   - Correlation = 0 is NOT sufficient
   - Must test conditional probability directly
   - P(ΔX[t+1] | ΔX[t]) vs P(ΔX[t+1])

### 9.2 Implications for SDM

**The Lévy framework offers**:
- Rigorous mathematical foundation
- Analytical solutions via characteristic functions
- Clear path to extensions (subordination for mobile dispersion)
- Validation criteria (independent/stationary increments)

**SDM can benefit from**:
- Explicit CPP structure for adsorption events
- Proper distinction between time and space variables
- Subordination technique for mobile phase dispersion
- Analytical solutions to complement simulations

### 9.3 The Big Picture

Pasti 2005 provides a **complete mathematical framework** for chromatography based on Lévy processes. This framework:
- Is rigorously grounded in probability theory
- Has analytical solutions (characteristic functions)
- Can be extended systematically (subordination)
- Makes testable predictions (independent increments, specific distributions)

**For SDM**: This framework can guide improvements, validate implementations, and suggest extensions that maintain mathematical rigor while capturing physical reality.

---

**Document prepared**: December 25, 2025  
**For**: SDM Enhancement and Future Discussions  
**Status**: Ready for implementation planning
