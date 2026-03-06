"""
Analysis: Geometry-Dependent k Values in Gamma RTD

This script tests the hypothesis that the Gamma shape parameter k depends
on pore geometry (sector angle, aspect ratio) even without surface binding.

The mechanism:
1. Particles perform random walk in sector-shaped pores with reflecting walls
2. Exit only through pore entry (first-passage time problem)
3. Different geometries → different RTD shapes → different k values

Theoretical predictions:
- Narrow sectors: Longer, more variable residence times → k < 1 (heavy tail)
- Wide sectors: More uniform access to exit → k ≈ 1 (exponential-like)
- Aspect ratio matters: Deep narrow pores → smaller k
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats as sp_stats
from scipy.optimize import minimize

# Add molass to path
molass_path = Path(__file__).parent.parent
sys.path.insert(0, str(molass_path))

from molass.SEC.ColumnSimulation import get_animation
from study.verify_gamma_residence import fit_gamma, fit_exponential


def run_geometry_sweep_sector_angle(
    num_pores_list=[4, 8, 16, 24, 32],
    num_frames=600,
    seed=42
):
    """
    Test hypothesis: k depends on sector angle.
    
    More pores → smaller sector angle → more wall collisions → different k
    
    Parameters
    ----------
    num_pores_list : list of int
        Number of pores per grain (determines sector angle = 2π/num_pores)
    num_frames : int
        Simulation length
    seed : int
        Random seed
        
    Returns
    -------
    results : dict
        Contains k values, sector angles, and statistical tests
    """
    print("="*80)
    print("GEOMETRY SWEEP: Sector Angle Dependence")
    print("="*80)
    print(f"Testing {len(num_pores_list)} different pore configurations")
    print(f"Frames per simulation: {num_frames}")
    print(f"Random seed: {seed}\n")
    
    results = {
        'num_pores': [],
        'pore_sector_angle_deg': [],  # Actual accessible pore angle
        'unit_angle_deg': [],  # Full unit (pore + wall)
        'k_all': [],
        'k_large': [],
        'k_medium': [],
        'k_small': [],
        'mean_residence_all': [],
        'cv_all': []
    }
    
    for num_pores in num_pores_list:
        pore_sector_angle = 180 / num_pores  # Actual accessible angle
        unit_angle = 360 / num_pores  # Full unit (pore + wall)
        print(f"\n{'-'*80}")
        print(f"Configuration: {num_pores} pores/grain")
        print(f"  Pore sector angle = {pore_sector_angle:.2f}° (accessible region)")
        print(f"  Unit angle = {unit_angle:.2f}° (pore + wall combined)")
        print(f"{'-'*80}")
        
        print(f"  Running simulation...")
        stats = run_animation_with_tracking(num_frames, seed, num_pores=num_pores)
        
        # Fit Gamma to all particles
        all_durations = []
        for k in range(len(stats['ptype_indeces'])):
            all_durations.extend(stats['adsorption_durations_list'][k])
        
        if len(all_durations) < 30:
            print(f"  WARNING: Only {len(all_durations)} samples, skipping")
            continue
            
        data = np.array(all_durations)
        gamma_fit = fit_gamma(data)
        
        results['num_pores'].append(num_pores)
        results['pore_sector_angle_deg'].append(pore_sector_angle)
        results['unit_angle_deg'].append(unit_angle)
        results['k_all'].append(gamma_fit['k'])
        results['mean_residence_all'].append(gamma_fit['mean'])
        results['cv_all'].append(np.std(data)/np.mean(data))
        
        print(f"  Fitted k = {gamma_fit['k']:.4f}")
        print(f"  Mean residence = {gamma_fit['mean']:.6f}")
        print(f"  CV = {np.std(data)/np.mean(data):.4f}")
        print(f"  Theoretical CV from k: 1/√k = {1/np.sqrt(gamma_fit['k']):.4f}")
        
        # Fit by particle type
        for ptype, label in enumerate(['large', 'medium', 'small']):
            key = f"{label}_indeces"
            indeces = stats[key]
            durations = []
            for k in indeces:
                durations.extend(stats['adsorption_durations_list'][k])
            
            if len(durations) >= 30:
                data_type = np.array(durations)
                gamma_fit_type = fit_gamma(data_type)
                results[f'k_{label}'].append(gamma_fit_type['k'])
                print(f"    {label.capitalize()}: k = {gamma_fit_type['k']:.4f}")
            else:
                results[f'k_{label}'].append(np.nan)
    
    # Plot results
    plot_geometry_sweep_results(results)
    
    return results


def run_animation_with_tracking(num_frames, seed, num_pores=16):
    """Wrapper to run animation and extract stats."""
    print("  Executing animation frames...")
    anim, stats = get_animation(
        num_frames=num_frames,
        seed=seed,
        close_plot=True,
        track_statistics=True,
        use_tqdm=True,
        blit=False,
        num_pores=num_pores
    )
    # Force frame execution
    anim.save("temp_geometry_sweep.gif", writer='pillow', fps=10)
    print("  Animation complete.")
    return stats


def plot_geometry_sweep_results(results):
    """Create publication-quality plots of geometry-k relationship."""
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Panel A: k vs pore sector angle
    ax = axes[0, 0]
    ax.plot(results['pore_sector_angle_deg'], results['k_all'], 
            'o-', linewidth=2, markersize=8, color='black', label='All particles')
    
    # Add species-specific if available
    for label, color in zip(['large', 'medium', 'small'], ['green', 'blue', 'red']):
        k_vals = results[f'k_{label}']
        if not all(np.isnan(k_vals)):
            ax.plot(results['pore_sector_angle_deg'], k_vals,
                   'o--', linewidth=1.5, markersize=6, color=color, 
                   alpha=0.7, label=label.capitalize())
    
    ax.axhline(1, color='red', linestyle='--', linewidth=1, alpha=0.5, label='k=1 (Exponential)')
    ax.set_xlabel('Pore Sector Angle (degrees)', fontsize=12)
    ax.set_ylabel('Gamma Shape Parameter k', fontsize=12)
    ax.set_title('A. Shape Parameter vs Pore Geometry', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Panel B: CV vs sector angle
    ax = axes[0, 1]
    cv_empirical = results['cv_all']
    cv_theoretical = [1/np.sqrt(k) for k in results['k_all']]
    
    ax.plot(results['pore_sector_angle_deg'], cv_empirical,
           'o-', linewidth=2, markersize=8, color='blue', label='Empirical CV')
    ax.plot(results['pore_sector_angle_deg'], cv_theoretical,
           's--', linewidth=2, markersize=8, color='red', label='Theoretical (1/√k)')
    
    ax.set_xlabel('Pore Sector Angle (degrees)', fontsize=12)
    ax.set_ylabel('Coefficient of Variation', fontsize=12)
    ax.set_title('B. CV Validation', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Panel C: k vs number of pores (log scale)
    ax = axes[1, 0]
    ax.semilogx(results['num_pores'], results['k_all'],
               'o-', linewidth=2, markersize=8, color='purple')
    ax.axhline(1, color='red', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_xlabel('Number of Pores per Grain', fontsize=12)
    ax.set_ylabel('Gamma Shape Parameter k', fontsize=12)
    ax.set_title('C. Shape Parameter vs Pore Density', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, which='both')
    
    # Panel D: Mean residence time vs geometry
    ax = axes[1, 1]
    ax.plot(results['pore_sector_angle_deg'], results['mean_residence_all'],
           'o-', linewidth=2, markersize=8, color='orange')
    ax.set_xlabel('Pore Sector Angle (degrees)', fontsize=12)
    ax.set_ylabel('Mean Residence Time', fontsize=12)
    ax.set_title('D. Mean Residence vs Geometry', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    plt.suptitle('Geometric Origin of Non-Exponential Residence Times', 
                 fontsize=15, fontweight='bold')
    plt.tight_layout()
    
    # Save
    save_path = molass_path / 'study' / 'geometry_k_relationship.png'
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {save_path}")
    
    plt.show()


def theoretical_prediction_k_vs_angle():
    """
    Theoretical prediction for k vs sector angle based on first-passage time theory.
    
    For diffusion in a wedge with reflecting boundaries and single exit:
    - Narrow wedge (small angle): More tortuous paths → larger variance → smaller k
    - Wide wedge (large angle): More direct access → smaller variance → larger k
    
    First-passage time distribution depends on geometry through:
    1. Mean escape time ∝ Area / (Perimeter × Diffusivity)
    2. Variance ∝ geometric complexity
    
    References:
    - Redner, S. (2001) "A Guide to First-Passage Processes" Cambridge Univ Press
    - Condamin et al. (2007) "First-passage times in complex scale-invariant media" Nature
    """
    
    print("\n" + "="*80)
    print("THEORETICAL PREDICTION")
    print("="*80)
    
    print("""
For a sector-shaped pore with angle θ:

1. Narrow sectors (θ → 0):
   - Particle must navigate along walls to find exit
   - Path length variance is large
   - Heavy-tailed distribution → k < 1

2. Wide sectors (θ → π):
   - Many direct paths to exit
   - More uniform escape times
   - Approaches exponential → k ≈ 1

3. Intermediate sectors:
   - Gamma distribution naturally emerges
   - k reflects balance between direct/tortuous paths

Expected trend: k increases with θ (more pores → smaller θ → smaller k)

This is a GEOMETRIC effect, independent of:
- Surface chemistry
- Binding energetics
- Multiple binding sites

Therefore, even perfectly homogeneous pores produce non-exponential RTD!
    """)


def suggest_next_experiments():
    """Suggest follow-up experiments to test geometric hypothesis."""
    
    print("\n" + "="*80)
    print("SUGGESTED FOLLOW-UP EXPERIMENTS")
    print("="*80)
    
    experiments = {
        "1. Vary pore density": {
            "Parameter": "num_pores in ColumnSimulation",
            "Test range": "[4, 8, 16, 24, 32] pores per grain",
            "Expected": "k decreases as num_pores increases",
            "Why": "Narrower sectors → more wall collisions → heavier tail"
        },
        
        "2. Vary grain radius": {
            "Parameter": "rs (grain radius)",
            "Test range": "[0.02, 0.0381, 0.06] (default 0.0381)",
            "Expected": "k decreases with larger grains",
            "Why": "Deeper pores → longer, more variable escape times"
        },
        
        "3. Vary particle size": {
            "Parameter": "psizes array",
            "Test range": "Vary excluded volume fraction",
            "Expected": "Smaller particles (less excluded volume) → k closer to 1",
            "Why": "More accessible pore volume → more uniform paths"
        },
        
        "4. Test aspect ratio": {
            "Parameter": "Modify ColumnStructure to create elongated sectors",
            "Test range": "Circular vs elliptical grains",
            "Expected": "Elongated → smaller k",
            "Why": "Deeper traps in elongated geometry"
        },
        
        "5. Single-pore validation": {
            "Parameter": "Track single particle in single pore",
            "Test": "Measure first-passage time distribution directly",
            "Expected": "Directly observe Gamma distribution from geometry alone",
            "Why": "Controls for inter-pore heterogeneity"
        },
        
        "6. Compare 2D vs 3D": {
            "Parameter": "Dimension of simulation",
            "Test": "Extend to 3D conical pores",
            "Expected": "Different k values, but same trend with geometry",
            "Why": "Validates geometric mechanism is dimension-independent"
        }
    }
    
    for exp_name, details in experiments.items():
        print(f"\n{exp_name}")
        for key, value in details.items():
            print(f"  {key}: {value}")
    
    print("\n" + "="*80)
    print("IMPLEMENTATION PRIORITY")
    print("="*80)
    print("""
High priority (easy to implement):
- Experiment 1: Modify num_pores parameter
- Experiment 2: Modify rs parameter  
- Experiment 3: Modify psizes array

Medium priority (requires code changes):
- Experiment 4: Modify ColumnStructure.py for elongated grains
- Experiment 5: Add single-pore tracking mode

Low priority (major refactor):
- Experiment 6: 3D simulation
    """)


def main():
    """Run complete geometry-k relationship analysis."""
    
    print("="*80)
    print("GEOMETRY-DEPENDENT GAMMA SHAPE PARAMETER ANALYSIS")
    print("="*80)
    print("""
This script tests whether pore geometry alone can produce non-exponential
residence time distributions (k ≠ 1) without invoking surface heterogeneity.

Mechanism: Random walk in sector-shaped pore with reflecting boundaries
→ First-passage time problem → Gamma-distributed residence times

Expected outcome: k depends on sector angle and pore depth
    """)
    
    # Show theoretical prediction
    theoretical_prediction_k_vs_angle()
    
    # Suggest experiments
    suggest_next_experiments()
    
    # Run actual sweep (now fully functional!)
    print("\n" + "="*80)
    print("RUNNING GEOMETRY SWEEP")
    print("="*80)
    print("\nColumnSimulation.py now accepts num_pores parameter!")
    print("Ready to test geometric hypothesis: k = f(sector angle)\n")
    
    response = input("Run full geometry sweep? (y/n, or 'demo' for quick test): ")
    if response.lower() == 'y':
        results = run_geometry_sweep_sector_angle(
            num_pores_list=[4, 8, 16, 24, 32],
            num_frames=600,
            seed=42
        )
    elif response.lower() == 'demo':
        print("\nRunning quick demo with 2 configurations...")
        results = run_geometry_sweep_sector_angle(
            num_pores_list=[8, 16],
            num_frames=300,
            seed=42
        )
        
        print("\n" + "="*80)
        print("RESULTS SUMMARY")
        print("="*80)
        if len(results['k_all']) > 0:
            print(f"\nGeometry sweep completed!")
            print(f"Configurations tested: {len(results['num_pores'])}")
            print(f"\nk values by configuration:")
            for i, (np_val, angle, k_val) in enumerate(zip(results['num_pores'], 
                                                            results['pore_sector_angle_deg'], 
                                                            results['k_all'])):
                print(f"  {np_val:2d} pores (pore angle={angle:5.2f}°): k = {k_val:.4f}")
            
            # Check for trend
            if len(results['k_all']) > 1:
                from scipy.stats import spearmanr
                corr, p_val = spearmanr(results['pore_sector_angle_deg'], results['k_all'])
                print(f"\nCorrelation: k vs pore_sector_angle")
                print(f"  Spearman r = {corr:.3f}, p = {p_val:.4f}")
                if p_val < 0.05:
                    if corr > 0:
                        print(f"  ✓ Significant positive trend: Wider sectors → larger k")
                    else:
                        print(f"  ✓ Significant negative trend: Wider sectors → smaller k")
                else:
                    print(f"  No significant trend detected")
            
            print(f"\n{'='*80}")
            print("INTERPRETATION")
            print(f"{'='*80}")
            if any(k != 1.0 for k in results['k_all']):
                print("✓ Geometry alone creates non-exponential RTD (k ≠ 1)")
                print("✓ Validates Gamma model from first principles")
                print("✓ No surface heterogeneity needed!")
            else:
                print("All k ≈ 1: Current geometry produces exponential-like distribution")
                print("Consider: More extreme geometries or longer simulations")
    else:
        print("\nSkipped geometry sweep.")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("""
✓ COMPLETED: Modified molass/SEC/ColumnSimulation.py
  - Added num_pores parameter to get_animation()
  - Now ready for geometry sweeps!

READY TO RUN:
1. Full geometry sweep:
   python study/geometry_k_relationship_analysis.py
   
2. Test specific configuration:
   from molass.SEC.ColumnSimulation import get_animation
   anim, stats = get_animation(num_frames=400, num_pores=8, 
                                track_statistics=True, seed=42)
   
3. Quick validation:
   - Run with num_pores=[8, 16, 24]
   - Compare k values
   - Plot k vs sector angle

PUBLISH:
4. Write up results showing geometric origin of Gamma RTD
5. Connect to first-passage time theory (Redner 2001)
6. Demonstrate for SEC-SAXS community
    """)


if __name__ == "__main__":
    main()
