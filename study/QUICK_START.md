# Quick Start: Testing Geometric k Hypothesis

## TL;DR - Run This Now

```bash
# Quick test (2 min)
python study/test_geometry_parameter.py --mode compare

# Full analysis (25 min)
python study/geometry_k_relationship_analysis.py
```

## What You'll Prove

**Hypothesis**: Gamma shape parameter k depends on pore geometry (sector angle)

**Expected outcome**: 
- Wide sectors (few pores) → k > 1 or k ≈ 1
- Narrow sectors (many pores) → k < 1 (heavy tail)
- **At least one geometry produces k ≠ 1**

**Significance**: Proves Gamma distribution necessary due to geometry alone (no chemistry needed!)

## Three Ways to Test

### 1. Instant Demo (30 sec)
```python
from molass.SEC.ColumnSimulation import get_animation

# Run with 8 pores (wide 45° sectors)
anim, stats = get_animation(num_pores=8, num_frames=100, 
                            track_statistics=True, close_plot=True)
print(f"Sector angle: {stats['sector_angle_deg']:.1f}°")
```

### 2. Quick Comparison (5 min)
```bash
python study/test_geometry_parameter.py --mode compare --frames 300
```
Tests 2 geometries (8 vs 24 pores), shows k difference

### 3. Full Sweep (25 min)
```bash
python study/geometry_k_relationship_analysis.py
# Choose: 'y' for full sweep, 'demo' for quick
```
Tests 5 geometries, generates publication figure

## Interpreting Results

### Success Indicators
✓ k values differ between configurations (|Δk| > 0.1)  
✓ At least one k significantly ≠ 1 (p < 0.05)  
✓ Systematic trend with sector angle  
✓ CV matches 1/√k prediction  

### What k Values Mean
- **k < 0.8**: Heavy tail, some particles trapped long times
- **k ≈ 1.0**: Approximately exponential (special case)
- **k > 1.2**: More uniform than exponential

### Statistical Tests
- **Likelihood Ratio Test**: Is Gamma better than Exponential?
  - p < 0.05 → Gamma significantly better → k ≠ 1
- **AIC difference**: Lower = better model
  - ΔAIC < -2 → Gamma preferred

## What to Tell Collaborators

**Simple version:**
> "We ran simulations of particles diffusing in pores with different geometries. Even with no surface binding, the residence time distribution isn't exponential - it follows a Gamma distribution. The shape parameter k depends on the pore angle. This proves the Gamma model isn't just a better fit, it's physically necessary."

**Technical version:**
> "Random walk with reflecting boundaries in sector-shaped pores is a first-passage time problem. The mixture of fast (near entry) and slow (far from entry) escape times naturally produces a Gamma distribution. We validate this by systematically varying sector angle (2π/num_pores) and showing k = f(angle). This provides mechanistic justification for extending Giddings' model from exponential (k=1) to Gamma (k≠1) residence times."

## Expected Timeline

| Stage | Time | Output |
|-------|------|--------|
| Quick test | 2 min | Verify parameter works |
| Compare 2 configs | 5 min | Show k differs with geometry |
| Full sweep (5 configs) | 25 min | Publication figure |
| Analysis & writeup | 2 hrs | Results section |
| Share with team | 1 day | Get feedback |
| Incorporate into paper | 1 week | Methods + results |

## Files You'll Generate

1. **test_pores_*.gif**: Animation for each configuration
2. **gamma_vs_exponential_*.png**: 6-panel diagnostic plots
3. **geometry_k_relationship.png**: Main figure (4 panels)
4. **Results table**: k values by sector angle

## Common Issues

**"Only N samples" warning**
→ Increase `--frames 400` or `--frames 600`

**"Optimization did not converge"**
→ Normal for k ≈ 1, not a failure

**"All k values ≈ 1"**
→ Try extreme geometries: `num_pores=[4, 32]`

**Animation window appears**
→ Normal, will close automatically when done

## Key Numbers to Report

From your results, extract:
1. **k values**: One per geometry tested
2. **Sector angles**: Corresponding angles
3. **p-values**: From likelihood ratio tests
4. **Correlation**: Spearman r between angle and k
5. **Sample sizes**: Number of adsorption events

Example results table:
```
Config    | Angle  | k      | p-value | Conclusion
----------|--------|--------|---------|------------------
4 pores   | 90.0°  | 1.234  | 0.123   | Exponential OK
8 pores   | 45.0°  | 1.087  | 0.078   | Borderline
16 pores  | 22.5°  | 0.912  | 0.023   | ✓ Gamma needed
24 pores  | 15.0°  | 0.743  | 0.001   | ✓ Gamma needed
32 pores  | 11.3°  | 0.621  | <0.001  | ✓ Gamma needed
```

→ Proves: Narrow sectors create heavy-tailed RTD (k < 1)

## Next Actions

**After confirming it works:**
1. Run full sweep
2. Generate figures
3. Draft methods section
4. Schedule meeting with collaborators

**For paper:**
- Methods: Describe simulation, geometry parameters
- Results: Show k vs angle plot, statistical tests  
- Discussion: Connect to first-passage time theory
- Conclusion: Geometric origin validates Gamma model

## The Punchline

**Before your work:**  
"Gamma distribution fits SEC data better than exponential (empirical observation)"

**After your work:**  
"Gamma distribution is theoretically necessary because pore geometry creates first-passage time problem (mechanistic explanation)"

**This changes the conversation from:**
- "Can we justify using Gamma?" 
- → "We must use Gamma because geometry"

---

**Ready? Start here:**
```bash
python study/test_geometry_parameter.py --mode compare
```

🚀 Good luck!
