"""
Verify GEC Model Assumptions from Animation Data

This script runs the SEC animation with statistics tracking enabled and tests:
1. Exponential distribution of adsorption durations (Dondi Eq. 41)
2. Poisson distribution of adsorption counts (Dondi Eq. 42)
3. Comparison of empirical vs theoretical characteristic functions

Usage:
    python verify_gec_assumptions.py
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats as sp_stats
from pathlib import Path

# Add molass to path
molass_path = Path(__file__).parent.parent
sys.path.insert(0, str(molass_path))

from molass.SEC.ColumnSimulation import get_animation

def run_animation_with_tracking(num_frames=400, seed=42):
    """
    Run animation and collect statistics.
    
    Returns
    -------
    stats : dict
        Dictionary containing adsorption statistics
    """
    print(f"Running animation with {num_frames} frames, seed={seed}...")
    anim, stats_dict = get_animation(
        num_frames=num_frames,
        seed=seed,
        close_plot=True,
        track_statistics=True,
        use_tqdm=True,
        blit=False
    )
    
    # Must save the animation to actually execute all frames
    print("Executing animation frames to collect statistics...")
    # import tempfile
    # with tempfile.NamedTemporaryFile(suffix='.gif', delete=True) as tmp:
    #     anim.save(tmp.name, writer='pillow', fps=10)
    anim.save("temp.gif")
    
    print("Animation complete.")
    return stats_dict


def test_exponential_egress(stats, particle_type=None, alpha=0.05):
    """
    Test if adsorption durations follow exponential distribution.
    
    Parameters
    ----------
    stats : dict
        Statistics from animation
    particle_type : int, optional
        0=large, 1=medium, 2=small. If None, test all particles.
    alpha : float
        Significance level for KS test
    
    Returns
    -------
    result : dict
        Test results with p-values and fitted parameters
    """
    print("\n" + "="*70)
    print("TEST 1: Exponential Egress Time Distribution (Dondi Eq. 41)")
    print("="*70)
    
    # Select particles
    if particle_type is not None:
        type_names = ['Large (green)', 'Medium (blue)', 'Small (red)']
        type_keys = ['large_indeces', 'middle_indeces', 'small_indeces']
        particle_indeces = stats[type_keys[particle_type]]
        print(f"Testing {type_names[particle_type]} particles only")
    else:
        particle_indeces = np.arange(len(stats['ptype_indeces']))
        print("Testing all particles combined")
    
    # Collect all durations for selected particles
    all_durations = []
    for k in particle_indeces:
        all_durations.extend(stats['adsorption_durations_list'][k])
    
    all_durations = np.array(all_durations)
    print(f"Total number of adsorption events: {len(all_durations)}")
    
    if len(all_durations) == 0:
        print("WARNING: No adsorption events recorded!")
        return None
    
    # Fit exponential distribution
    tau_bar = np.mean(all_durations)
    print(f"Mean adsorption time: τ̄ = {tau_bar:.6f}")
    print(f"Std adsorption time: σ = {np.std(all_durations):.6f}")
    print(f"Expected std for exponential: τ̄ = {tau_bar:.6f}")
    
    # Kolmogorov-Smirnov test
    ks_stat, p_value = sp_stats.kstest(
        all_durations,
        lambda x: sp_stats.expon.cdf(x, scale=tau_bar)
    )
    
    print(f"\nKolmogorov-Smirnov Test:")
    print(f"  KS statistic: {ks_stat:.4f}")
    print(f"  p-value: {p_value:.4f}")
    
    if p_value > alpha:
        print(f"  ✓ PASS: Cannot reject exponential distribution (p > {alpha})")
    else:
        print(f"  ✗ FAIL: Reject exponential distribution (p ≤ {alpha})")
    
    # Plot histogram vs theoretical
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Histogram
    ax1.hist(all_durations, bins=30, density=True, alpha=0.6, 
             label='Empirical', color='steelblue', edgecolor='black')
    
    x_theory = np.linspace(0, all_durations.max(), 200)
    y_theory = (1/tau_bar) * np.exp(-x_theory/tau_bar)
    ax1.plot(x_theory, y_theory, 'r-', linewidth=2, 
             label=f'Exponential(τ̄={tau_bar:.4f})')
    
    ax1.set_xlabel('Adsorption Duration')
    ax1.set_ylabel('Probability Density')
    ax1.set_title('Egress Time Distribution')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Q-Q plot
    sorted_data = np.sort(all_durations)
    theoretical_quantiles = sp_stats.expon.ppf(
        np.linspace(0.01, 0.99, len(sorted_data)), 
        scale=tau_bar
    )
    
    ax2.scatter(theoretical_quantiles, sorted_data, alpha=0.5, s=10)
    lims = [0, max(theoretical_quantiles.max(), sorted_data.max())]
    ax2.plot(lims, lims, 'r--', linewidth=2, label='Perfect fit')
    ax2.set_xlabel('Theoretical Exponential Quantiles')
    ax2.set_ylabel('Sample Quantiles')
    ax2.set_title('Q-Q Plot')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(molass_path / 'study' / 'egress_time_test.png', dpi=150)
    print(f"\nPlot saved to: study/egress_time_test.png")
    
    return {
        'tau_bar': tau_bar,
        'ks_stat': ks_stat,
        'p_value': p_value,
        'passed': p_value > alpha,
        'n_events': len(all_durations)
    }


def test_poisson_ingress(stats, particle_type=None, alpha=0.05):
    """
    Test if adsorption counts follow Poisson distribution.
    
    Parameters
    ----------
    stats : dict
        Statistics from animation
    particle_type : int, optional
        0=large, 1=medium, 2=small. If None, test all particles.
    alpha : float
        Significance level for chi-square test
    
    Returns
    -------
    result : dict
        Test results with p-values and fitted parameters
    """
    print("\n" + "="*70)
    print("TEST 2: Poisson Ingress Count Distribution (Dondi Eq. 42)")
    print("="*70)
    
    # Select particles
    if particle_type is not None:
        type_names = ['Large (green)', 'Medium (blue)', 'Small (red)']
        type_keys = ['large_indeces', 'middle_indeces', 'small_indeces']
        particle_indeces = stats[type_keys[particle_type]]
        print(f"Testing {type_names[particle_type]} particles only")
    else:
        particle_indeces = np.arange(len(stats['ptype_indeces']))
        print("Testing all particles combined")
    
    # Get adsorption counts
    counts = stats['adsorption_counts'][particle_indeces]
    print(f"Number of particles: {len(counts)}")
    print(f"Mean adsorption count: n̄ = {np.mean(counts):.4f}")
    print(f"Variance: {np.var(counts):.4f}")
    print(f"Expected variance for Poisson: n̄ = {np.mean(counts):.4f}")
    
    # Fit Poisson distribution
    n_bar = np.mean(counts)
    
    # Chi-square goodness of fit test
    # Bin counts and compute expected frequencies
    max_count = int(counts.max())
    bins = np.arange(0, max_count + 2)
    observed_freq, _ = np.histogram(counts, bins=bins)
    
    # Expected frequencies from Poisson
    expected_freq = len(counts) * sp_stats.poisson.pmf(bins[:-1], n_bar)
    
    # Combine bins with expected frequency < 5
    combined_observed = []
    combined_expected = []
    temp_obs = 0
    temp_exp = 0
    
    for obs, exp in zip(observed_freq, expected_freq):
        temp_obs += obs
        temp_exp += exp
        if temp_exp >= 5:
            combined_observed.append(temp_obs)
            combined_expected.append(temp_exp)
            temp_obs = 0
            temp_exp = 0
    
    if temp_obs > 0:  # Add remaining
        if len(combined_observed) > 0:
            combined_observed[-1] += temp_obs
            combined_expected[-1] += temp_exp
        else:
            combined_observed.append(temp_obs)
            combined_expected.append(temp_exp)
    
    # Convert to arrays and normalize to ensure exact sum match
    combined_observed = np.array(combined_observed)
    combined_expected = np.array(combined_expected)
    
    # Renormalize expected to exactly match observed sum (fix floating point errors)
    expected_sum = combined_expected.sum()
    observed_sum = combined_observed.sum()
    combined_expected = combined_expected * (observed_sum / expected_sum)
    
    # Chi-square test (df = bins - 1 - num_parameters_estimated)
    chi2_stat, p_value = sp_stats.chisquare(combined_observed, combined_expected, ddof=1)
    
    print(f"\nChi-Square Goodness of Fit Test:")
    print(f"  Chi-square statistic: {chi2_stat:.4f}")
    print(f"  p-value: {p_value:.4f}")
    
    if p_value > alpha:
        print(f"  ✓ PASS: Cannot reject Poisson distribution (p > {alpha})")
    else:
        print(f"  ✗ FAIL: Reject Poisson distribution (p ≤ {alpha})")
    
    # Plot comparison
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Empirical PMF
    unique_counts, count_freq = np.unique(counts, return_counts=True)
    count_prob = count_freq / len(counts)
    
    ax.bar(unique_counts - 0.2, count_prob, width=0.4, 
           label='Empirical', alpha=0.7, color='steelblue', edgecolor='black')
    
    # Theoretical PMF
    x_theory = np.arange(0, max_count + 1)
    y_theory = sp_stats.poisson.pmf(x_theory, n_bar)
    
    ax.bar(x_theory + 0.2, y_theory, width=0.4,
           label=f'Poisson(n̄={n_bar:.2f})', alpha=0.7, color='coral', edgecolor='black')
    
    ax.set_xlabel('Number of Adsorptions (r_M)')
    ax.set_ylabel('Probability')
    ax.set_title('Ingress Count Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(molass_path / 'study' / 'ingress_count_test.png', dpi=150)
    print(f"\nPlot saved to: study/ingress_count_test.png")
    
    return {
        'n_bar': n_bar,
        'chi2_stat': chi2_stat,
        'p_value': p_value,
        'passed': p_value > alpha,
        'n_particles': len(counts)
    }


def compare_characteristic_functions(stats, particle_type=None):
    """
    Compare empirical vs theoretical characteristic functions.
    
    Parameters
    ----------
    stats : dict
        Statistics from animation
    particle_type : int, optional
        0=large, 1=medium, 2=small. If None, use all particles.
    """
    print("\n" + "="*70)
    print("TEST 3: Characteristic Function Comparison")
    print("="*70)
    
    # Select particles
    if particle_type is not None:
        type_names = ['Large (green)', 'Medium (blue)', 'Small (red)']
        type_keys = ['large_indeces', 'middle_indeces', 'small_indeces']
        particle_indeces = stats[type_keys[particle_type]]
        print(f"Testing {type_names[particle_type]} particles only")
    else:
        particle_indeces = np.arange(len(stats['ptype_indeces']))
        print("Testing all particles combined")
    
    # Get total adsorbed times
    t_S = stats['total_adsorbed_time'][particle_indeces]
    print(f"Number of particles: {len(t_S)}")
    print(f"Mean total adsorbed time: {np.mean(t_S):.6f}")
    
    # Estimate parameters
    all_durations = []
    for k in particle_indeces:
        all_durations.extend(stats['adsorption_durations_list'][k])
    tau_bar = np.mean(all_durations)
    n_bar = np.mean(stats['adsorption_counts'][particle_indeces])
    
    print(f"Fitted parameters: n̄ = {n_bar:.4f}, τ̄ = {tau_bar:.6f}")
    print(f"Expected mean t_S: n̄·τ̄ = {n_bar * tau_bar:.6f}")
    
    # Compute empirical CF
    omega_range = np.linspace(-2, 2, 100)
    cf_empirical = np.array([
        np.mean(np.exp(1j * omega * t_S)) for omega in omega_range
    ])
    
    # Theoretical CF from GEC model (Dondi Eq. 43)
    def gec_cf(omega, n_bar, tau_bar):
        """GEC characteristic function"""
        return np.exp(n_bar * (np.exp(1j * omega * tau_bar) - 1) / (1 - 1j * omega * tau_bar))
    
    cf_theoretical = gec_cf(omega_range, n_bar, tau_bar)
    
    # Plot comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Real part
    ax1.plot(omega_range, cf_empirical.real, 'o', markersize=4, 
             label='Empirical', alpha=0.6, color='steelblue')
    ax1.plot(omega_range, cf_theoretical.real, '-', linewidth=2,
             label='GEC Theory', color='red')
    ax1.set_xlabel('ω')
    ax1.set_ylabel('Re[φ(ω)]')
    ax1.set_title('Real Part of CF')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Imaginary part
    ax2.plot(omega_range, cf_empirical.imag, 'o', markersize=4,
             label='Empirical', alpha=0.6, color='steelblue')
    ax2.plot(omega_range, cf_theoretical.imag, '-', linewidth=2,
             label='GEC Theory', color='red')
    ax2.set_xlabel('ω')
    ax2.set_ylabel('Im[φ(ω)]')
    ax2.set_title('Imaginary Part of CF')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(molass_path / 'study' / 'cf_comparison.png', dpi=150)
    print(f"\nPlot saved to: study/cf_comparison.png")
    
    # Compute mean squared error
    mse = np.mean(np.abs(cf_empirical - cf_theoretical)**2)
    print(f"Mean squared error: {mse:.6f}")


def test_independence(stats, particle_type=None, alpha=0.05):
    """
    Test independence between adsorption count (r_M) and total adsorbed time (t_S).
    
    For a true Compound Poisson Process, r_M and t_S should be independent.
    This tests whether the simulation violates this critical assumption.
    
    Parameters
    ----------
    stats : dict
        Statistics from animation
    particle_type : int, optional
        0=large, 1=medium, 2=small. If None, test all particles.
    alpha : float
        Significance level for correlation test
    
    Returns
    -------
    result : dict
        Test results with correlation coefficient and p-value
    """
    print("\n" + "="*70)
    print("TEST 4: Independence of r_M and t_S (CPP Assumption)")
    print("="*70)
    
    # Select particles
    if particle_type is not None:
        type_names = ['Large (green)', 'Medium (blue)', 'Small (red)']
        type_keys = ['large_indeces', 'middle_indeces', 'small_indeces']
        particle_indeces = stats[type_keys[particle_type]]
        print(f"Testing {type_names[particle_type]} particles only")
    else:
        particle_indeces = np.arange(len(stats['ptype_indeces']))
        print("Testing all particles combined")
    
    # Get data
    r_M = stats['adsorption_counts'][particle_indeces]
    t_S = stats['total_adsorbed_time'][particle_indeces]
    
    # Filter out particles with no adsorptions
    valid = r_M > 0
    r_M_valid = r_M[valid]
    t_S_valid = t_S[valid]
    
    print(f"Number of particles: {len(particle_indeces)}")
    print(f"Particles with adsorptions: {len(r_M_valid)}")
    
    if len(r_M_valid) < 3:
        print("WARNING: Too few particles with adsorptions for correlation test!")
        return None
    
    # Pearson correlation
    corr_coef, p_value = sp_stats.pearsonr(r_M_valid, t_S_valid)
    
    print(f"\nPearson Correlation:")
    print(f"  r_M vs t_S: ρ = {corr_coef:.4f}")
    print(f"  p-value: {p_value:.4f}")
    
    if p_value > alpha:
        print(f"  ✓ PASS: Cannot reject independence (p > {alpha})")
        print(f"  → r_M and t_S appear independent (CPP assumption holds)")
    else:
        print(f"  ✗ FAIL: Reject independence (p ≤ {alpha})")
        if corr_coef > 0:
            print(f"  → Positive correlation: More adsorptions → longer total time")
        else:
            print(f"  → Negative correlation: More adsorptions → shorter total time")
    
    # Spearman correlation (robust to nonlinearity)
    spearman_corr, spearman_p = sp_stats.spearmanr(r_M_valid, t_S_valid)
    print(f"\nSpearman Rank Correlation (robust):")
    print(f"  ρ_s = {spearman_corr:.4f}, p = {spearman_p:.4f}")
    
    # Plot scatter
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Scatter plot
    ax1.scatter(r_M_valid, t_S_valid, alpha=0.5, s=20, color='steelblue')
    
    # Add regression line if significant
    if p_value < alpha:
        z = np.polyfit(r_M_valid, t_S_valid, 1)
        p = np.poly1d(z)
        x_line = np.array([r_M_valid.min(), r_M_valid.max()])
        ax1.plot(x_line, p(x_line), "r--", linewidth=2, 
                label=f'Linear fit (ρ={corr_coef:.3f})')
        ax1.legend()
    
    ax1.set_xlabel('Adsorption Count (r_M)')
    ax1.set_ylabel('Total Adsorbed Time (t_S)')
    ax1.set_title(f'Independence Test\nρ = {corr_coef:.4f}, p = {p_value:.4f}')
    ax1.grid(True, alpha=0.3)
    
    # Conditional distributions: t_S | r_M
    unique_r_M = np.unique(r_M_valid)
    if len(unique_r_M) <= 10:  # Only if we have reasonable number of bins
        for r in unique_r_M[:5]:  # Plot first 5 for clarity
            mask = r_M_valid == r
            if mask.sum() >= 3:
                ax2.hist(t_S_valid[mask], bins=15, alpha=0.5, 
                        label=f'r_M = {int(r)}', density=True)
        
        ax2.set_xlabel('Total Adsorbed Time (t_S)')
        ax2.set_ylabel('Density')
        ax2.set_title('Distribution of t_S conditioned on r_M')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    else:
        # Hexbin plot for many unique values
        hexbin = ax2.hexbin(r_M_valid, t_S_valid, gridsize=20, cmap='Blues', mincnt=1)
        ax2.set_xlabel('Adsorption Count (r_M)')
        ax2.set_ylabel('Total Adsorbed Time (t_S)')
        ax2.set_title('Density (hexbin)')
        plt.colorbar(hexbin, ax=ax2, label='Count')
    
    plt.tight_layout()
    plt.savefig(molass_path / 'study' / 'independence_test.png', dpi=150)
    print(f"\nPlot saved to: study/independence_test.png")
    
    return {
        'corr_coef': corr_coef,
        'p_value': p_value,
        'spearman_corr': spearman_corr,
        'spearman_p': spearman_p,
        'passed': p_value > alpha,
        'n_particles': len(r_M_valid)
    }


def main(test_mode='separate'):
    """
    Run all verification tests.
    
    Parameters
    ----------
    test_mode : str
        'combined' : Test all particles together (violates monopore assumption)
        'separate' : Test each particle type separately (correct for SEC)
        'both' : Run both modes for comparison
    """
    # Run animation
    stats = run_animation_with_tracking(num_frames=400, seed=42)
    
    type_names = ['Large (green)', 'Medium (blue)', 'Small (red)']
    
    if test_mode in ['combined', 'both']:
        print("\n" + "="*70)
        print("COMBINED MODE (All particles together - violates monopore assumption)")
        print("="*70)
        
        # Test all particles together
        result_exp = test_exponential_egress(stats, particle_type=None)
        result_pois = test_poisson_ingress(stats, particle_type=None)
        compare_characteristic_functions(stats, particle_type=None)
    
    if test_mode in ['separate', 'both']:
        print("\n" + "="*70)
        print("SEPARATE MODE (Each species tested individually - correct for SEC)")
        print("="*70)
        
        results_by_type = {'exp': [], 'pois': [], 'indep': []}
        
        # Test each particle type separately
        for ptype in range(3):
            print(f"\n{'='*70}")
            print(f"ANALYZING {type_names[ptype].upper()} PARTICLES")
            print("="*70)
            
            result_exp = test_exponential_egress(stats, particle_type=ptype)
            result_pois = test_poisson_ingress(stats, particle_type=ptype)
            result_indep = test_independence(stats, particle_type=ptype)
            compare_characteristic_functions(stats, particle_type=ptype)
            
            results_by_type['exp'].append(result_exp)
            results_by_type['pois'].append(result_pois)
            results_by_type['indep'].append(result_indep)
        
        # Summary comparison
        print("\n" + "="*70)
        print("SUMMARY BY PARTICLE TYPE")
        print("="*70)
        print(f"{'Type':<15} {'n̄ (adsorptions)':<20} {'τ̄ (residence)':<20} {'Exp Test':<15} {'Poisson Test':<15} {'Independence':<15}")
        print("-" * 105)
        
        for ptype in range(3):
            exp_res = results_by_type['exp'][ptype]
            pois_res = results_by_type['pois'][ptype]
            indep_res = results_by_type['indep'][ptype]
            
            if exp_res and pois_res and indep_res:
                exp_status = "✓ PASS" if exp_res['passed'] else "✗ FAIL"
                pois_status = "✓ PASS" if pois_res['passed'] else "✗ FAIL"
                indep_status = "✓ PASS" if indep_res['passed'] else f"✗ FAIL (ρ={indep_res['corr_coef']:.3f})"
                
                print(f"{type_names[ptype]:<15} {pois_res['n_bar']:<20.4f} {exp_res['tau_bar']:<20.6f} "
                      f"{exp_status:<15} {pois_status:<15} {indep_status:<15}")
        
        print("\nInterpretation:")
        print("- Large particles: Excluded from most pores → low n̄")
        print("- Small particles: Enter all pores → high n̄")
        print("- This is SIZE EXCLUSION CHROMATOGRAPHY in action!")
        print("\nIndependence test:")
        print("- If r_M and t_S are correlated → CPP assumption violated")
        print("- Possible causes: size exclusion, temporal constraints, spatial coupling")
    
    print("\nAll plots saved to study/ directory.")
    plt.show()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Verify GEC model assumptions from SEC animation')
    parser.add_argument('--mode', choices=['combined', 'separate', 'both'], 
                        default='separate',
                        help='Test mode: combined (all particles), separate (by type), both')
    args = parser.parse_args()
    
    main(test_mode=args.mode)
