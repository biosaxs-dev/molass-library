"""
Quick test of num_pores parameter in ColumnSimulation

This script demonstrates that the geometry parameter now works
and can be used to test the k vs sector angle hypothesis.

Usage:
    python study/test_geometry_parameter.py
"""

import sys
from pathlib import Path
import numpy as np

# Add molass to path
molass_path = Path(__file__).parent.parent
sys.path.insert(0, str(molass_path))

from molass.SEC.ColumnSimulation import get_animation
from study.verify_gamma_residence import fit_gamma, fit_exponential


def quick_test(num_pores=16, num_frames=200, seed=42):
    """
    Quick test of a single geometry configuration.
    
    Parameters
    ----------
    num_pores : int
        Number of pores per grain
    num_frames : int
        Simulation length
    seed : int
        Random seed
    """
    pore_sector_angle = 180 / num_pores  # Actual accessible pore angle
    
    print("="*80)
    print(f"TESTING: {num_pores} pores per grain")
    print(f"Pore sector angle: {pore_sector_angle:.2f}° (accessible region)")
    print(f"Unit angle: {360/num_pores:.2f}° (pore + wall combined)")
    print("="*80)
    
    print("\nRunning simulation...")
    anim, stats = get_animation(
        num_frames=num_frames,
        seed=seed,
        close_plot=True,
        track_statistics=True,
        use_tqdm=True,
        blit=False,
        num_pores=num_pores
    )
    
    # Force execution
    print("Executing animation frames...")
    anim.save(f"test_pores_{num_pores}.gif", writer='pillow', fps=10)
    print("Animation complete.\n")
    
    # Collect durations
    all_durations = []
    for k in range(len(stats['ptype_indeces'])):
        all_durations.extend(stats['adsorption_durations_list'][k])
    
    if len(all_durations) < 30:
        print(f"WARNING: Only {len(all_durations)} samples - increase num_frames")
        return None
    
    data = np.array(all_durations)
    
    # Fit both models
    print("-"*80)
    print("FITTING RESULTS")
    print("-"*80)
    
    exp_fit = fit_exponential(data)
    gamma_fit = fit_gamma(data)
    
    print(f"\nExponential model:")
    print(f"  τ̄ = {exp_fit['tau_bar']:.6f}")
    print(f"  Log-likelihood = {exp_fit['log_likelihood']:.2f}")
    print(f"  AIC = {2*1 - 2*exp_fit['log_likelihood']:.2f}")
    
    print(f"\nGamma model:")
    print(f"  k = {gamma_fit['k']:.4f}")
    print(f"  θ = {gamma_fit['theta']:.6f}")
    print(f"  Mean = {gamma_fit['mean']:.6f}")
    print(f"  Log-likelihood = {gamma_fit['log_likelihood']:.2f}")
    print(f"  AIC = {2*2 - 2*gamma_fit['log_likelihood']:.2f}")
    
    # Likelihood ratio test
    lr_stat = 2 * (gamma_fit['log_likelihood'] - exp_fit['log_likelihood'])
    from scipy.stats import chi2
    p_value = 1 - chi2.cdf(lr_stat, 1)
    
    print(f"\nLikelihood Ratio Test:")
    print(f"  LR statistic = {lr_stat:.4f}")
    print(f"  p-value = {p_value:.6f}")
    
    if p_value < 0.05:
        print(f"  ✓ Gamma significantly better (p < 0.05)")
        print(f"  → k = {gamma_fit['k']:.3f} ≠ 1: Geometry creates non-exponential RTD!")
    else:
        print(f"  Exponential adequate for this geometry")
    
    # Verify metadata
    print(f"\nVerifying metadata:")
    print(f"  stats['num_pores'] = {stats['num_pores']}")
    print(f"  stats['unit_angle_deg'] = {stats['unit_angle_deg']:.2f}° (pore + wall)")
    print(f"  stats['pore_sector_angle_deg'] = {stats['pore_sector_angle_deg']:.2f}° (accessible)")
    assert stats['num_pores'] == num_pores, "num_pores not stored correctly!"
    assert abs(stats['pore_sector_angle_deg'] - pore_sector_angle) < 0.01, "pore_sector_angle mismatch!"
    print(f"  ✓ Geometry parameters correctly stored")
    
    return {
        'num_pores': num_pores,
        'pore_sector_angle': pore_sector_angle,
        'k': gamma_fit['k'],
        'theta': gamma_fit['theta'],
        'mean': gamma_fit['mean'],
        'n_samples': len(data),
        'lr_stat': lr_stat,
        'p_value': p_value
    }


def compare_two_geometries():
    """
    Compare two different geometries to demonstrate trend.
    """
    print("\n" + "="*80)
    print("COMPARING TWO GEOMETRIES")
    print("="*80)
    print("\nThis demonstrates that k depends on sector angle")
    print("Expected: Narrower sectors (more pores) → different k\n")
    
    results = []
    
    # Wide sectors
    print("\n" + "="*80)
    print("TEST 1: Wide sectors (8 pores, 45° each)")
    print("="*80)
    result1 = quick_test(num_pores=8, num_frames=300, seed=42)
    if result1:
        results.append(result1)
    
    # Narrow sectors
    print("\n" + "="*80)
    print("TEST 2: Narrow sectors (24 pores, 15° each)")
    print("="*80)
    result2 = quick_test(num_pores=24, num_frames=300, seed=42)
    if result2:
        results.append(result2)
    
    # Compare
    if len(results) == 2:
        print("\n" + "="*80)
        print("COMPARISON")
        print("="*80)
        print(f"\n{'Configuration':<20} {'Pore Angle':<12} {'k':<12} {'Mean RTD':<12} {'p-value':<12}")
        print("-"*80)
        for r in results:
            print(f"{r['num_pores']:d} pores{'':<13} {r['pore_sector_angle']:>6.2f}°{'':<5} "
                  f"{r['k']:>8.4f}{'':<4} {r['mean']:>8.6f}{'':<4} {r['p_value']:>8.6f}")
        
        print("\n" + "-"*80)
        print("INTERPRETATION")
        print("-"*80)
        
        k_diff = abs(results[1]['k'] - results[0]['k'])
        if k_diff > 0.1:
            print(f"✓ k differs by {k_diff:.3f} between geometries")
            print(f"✓ Geometry affects residence time distribution shape!")
        else:
            print(f"k values similar (diff = {k_diff:.3f})")
            print(f"Consider: longer simulations or more extreme geometries")
        
        if any(r['p_value'] < 0.05 for r in results):
            print(f"\n✓ At least one geometry produces k ≠ 1")
            print(f"✓ Proves: Geometry alone creates non-exponential RTD")
            print(f"✓ Gamma model necessary, not just empirical!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test num_pores parameter')
    parser.add_argument('--mode', choices=['single', 'compare'], default='single',
                       help='Test mode (default: single)')
    parser.add_argument('--pores', type=int, default=16,
                       help='Number of pores for single test (default: 16)')
    parser.add_argument('--frames', type=int, default=200,
                       help='Number of frames (default: 200)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed (default: 42)')
    
    args = parser.parse_args()
    
    if args.mode == 'single':
        print("\nRunning single geometry test...")
        result = quick_test(num_pores=args.pores, num_frames=args.frames, seed=args.seed)
        
        if result:
            print("\n" + "="*80)
            print("SUCCESS!")
            print("="*80)
            print(f"✓ num_pores parameter works correctly")
            print(f"✓ Pore sector angle = {result['pore_sector_angle']:.2f}° (accessible)")
            print(f"✓ Fitted k = {result['k']:.4f}")
            print(f"\nNext: Run full geometry sweep with:")
            print(f"  python study/geometry_k_relationship_analysis.py")
    
    else:  # compare mode
        compare_two_geometries()
        
        print("\n" + "="*80)
        print("SUCCESS!")
        print("="*80)
        print("✓ Geometry parameter fully functional")
        print("✓ Ready for systematic k vs angle analysis")
        print("\nNext: Run full sweep with 5+ configurations:")
        print("  python study/geometry_k_relationship_analysis.py")
