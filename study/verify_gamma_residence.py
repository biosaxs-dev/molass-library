"""
Test Gamma vs Exponential Residence Time Distribution

This script extends verify_gec_assumptions.py to test whether residence times
are better modeled by Gamma distribution (k ≠ 1) or Exponential (k = 1).

Statistical tests:
1. Fit both Exponential and Gamma to adsorption durations
2. Likelihood ratio test: Is k significantly different from 1?
3. AIC/BIC comparison: Which model is better?
4. Visual comparison: Q-Q plots, residuals

Usage:
    python verify_gamma_residence.py
    python verify_gamma_residence.py --frames 600 --seed 123
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats as sp_stats
from scipy.optimize import minimize
from pathlib import Path

# Add molass to path
molass_path = Path(__file__).parent.parent
sys.path.insert(0, str(molass_path))

from molass.SEC.ColumnSimulation import get_animation


def run_animation_with_tracking(num_frames=400, seed=42):
    """Run animation and collect statistics."""
    print(f"Running animation with {num_frames} frames, seed={seed}...")
    anim, stats_dict = get_animation(
        num_frames=num_frames,
        seed=seed,
        close_plot=True,
        track_statistics=True,
        use_tqdm=True,
        blit=False
    )
    
    print("Executing animation frames to collect statistics...")
    anim.save("temp.gif", writer='pillow', fps=10)
    print("Animation complete.")
    return stats_dict


def fit_exponential(data):
    """
    Fit exponential distribution to data.
    
    Returns
    -------
    params : dict
        Fitted parameters and log-likelihood
    """
    # MLE for exponential: tau_bar = mean
    tau_bar = np.mean(data)
    
    # Log-likelihood: sum(log(1/tau * exp(-x/tau)))
    log_lik = np.sum(np.log(1/tau_bar) - data/tau_bar)
    
    # KS test
    ks_stat, ks_p = sp_stats.kstest(data, lambda x: sp_stats.expon.cdf(x, scale=tau_bar))
    
    return {
        'distribution': 'Exponential',
        'tau_bar': tau_bar,
        'k': 1.0,  # Shape parameter for exponential
        'theta': tau_bar,  # Scale parameter
        'mean': tau_bar,
        'variance': tau_bar**2,
        'log_likelihood': log_lik,
        'n_params': 1,  # Only tau_bar
        'ks_stat': ks_stat,
        'ks_p': ks_p
    }


def fit_gamma(data):
    """
    Fit Gamma distribution to data using MLE.
    
    Returns
    -------
    params : dict
        Fitted parameters and log-likelihood
    """
    # Initial guess from method of moments
    mean = np.mean(data)
    var = np.var(data)
    k_init = mean**2 / var
    theta_init = var / mean
    
    # Clamp initial guess to reasonable range
    k_init = np.clip(k_init, 0.1, 10.0)
    theta_init = np.clip(theta_init, mean/100, mean*10)
    
    # Negative log-likelihood for Gamma using scipy
    def neg_log_lik(params):
        k, theta = params
        if k <= 0 or theta <= 0:
            return np.inf
        # Use scipy's built-in logpdf for numerical stability
        ll = np.sum(sp_stats.gamma.logpdf(data, a=k, scale=theta))
        if not np.isfinite(ll):
            return np.inf
        return -ll
    
    # Optimize
    result = minimize(neg_log_lik, [k_init, theta_init], 
                     bounds=[(0.01, 10.0), (mean/100, mean*10)],
                     method='L-BFGS-B')
    
    if not result.success:
        print(f"WARNING: Gamma optimization did not converge!")
        print(f"  Initial guess: k={k_init:.4f}, θ={theta_init:.6f}")
        print(f"  Final result: k={result.x[0]:.4f}, θ={result.x[1]:.6f}")
    
    k_fit, theta_fit = result.x
    log_lik = -result.fun
    
    # KS test
    ks_stat, ks_p = sp_stats.kstest(data, lambda x: sp_stats.gamma.cdf(x, k_fit, scale=theta_fit))
    
    return {
        'distribution': 'Gamma',
        'k': k_fit,
        'theta': theta_fit,
        'tau_bar': k_fit * theta_fit,  # Mean
        'mean': k_fit * theta_fit,
        'variance': k_fit * theta_fit**2,
        'log_likelihood': log_lik,
        'n_params': 2,  # k and theta
        'ks_stat': ks_stat,
        'ks_p': ks_p,
        'optimization_success': result.success
    }


def likelihood_ratio_test(exp_result, gamma_result, n_samples):
    """
    Perform likelihood ratio test: H0: k=1 (exponential) vs H1: k≠1 (gamma).
    
    Returns
    -------
    result : dict
        Test statistic, p-value, and conclusion
    """
    # LR statistic: 2 * (log_lik_gamma - log_lik_exp)
    # Under H0, this follows chi-square with df = difference in parameters
    lr_stat = 2 * (gamma_result['log_likelihood'] - exp_result['log_likelihood'])
    df = gamma_result['n_params'] - exp_result['n_params']  # Should be 1
    
    # P-value from chi-square distribution
    p_value = 1 - sp_stats.chi2.cdf(lr_stat, df)
    
    return {
        'lr_statistic': lr_stat,
        'df': df,
        'p_value': p_value,
        'significant_05': p_value < 0.05,
        'significant_01': p_value < 0.01
    }


def compute_information_criteria(result, n_samples):
    """Compute AIC and BIC."""
    k = result['n_params']
    log_lik = result['log_likelihood']
    
    # AIC = 2k - 2*log_lik
    aic = 2*k - 2*log_lik
    
    # BIC = k*log(n) - 2*log_lik
    bic = k*np.log(n_samples) - 2*log_lik
    
    return {'AIC': aic, 'BIC': bic}


def test_gamma_vs_exponential(stats, particle_type=None, alpha=0.05):
    """
    Compare Gamma vs Exponential fits to residence time data.
    
    Parameters
    ----------
    stats : dict
        Statistics from animation
    particle_type : int, optional
        0=large, 1=medium, 2=small. If None, test all particles.
    alpha : float
        Significance level
    
    Returns
    -------
    result : dict
        Complete comparison results
    """
    print("\n" + "="*80)
    print("GAMMA vs EXPONENTIAL RESIDENCE TIME DISTRIBUTION TEST")
    print("="*80)
    
    # Select particles
    if particle_type is not None:
        type_names = ['Large (green)', 'Medium (blue)', 'Small (red)']
        type_keys = ['large_indeces', 'middle_indeces', 'small_indeces']
        particle_indeces = stats[type_keys[particle_type]]
        test_label = type_names[particle_type]
        print(f"Testing {test_label} particles only")
    else:
        particle_indeces = np.arange(len(stats['ptype_indeces']))
        test_label = "All particles"
        print("Testing all particles combined")
    
    # Collect durations
    all_durations = []
    for k in particle_indeces:
        all_durations.extend(stats['adsorption_durations_list'][k])
    
    data = np.array(all_durations)
    n_samples = len(data)
    
    print(f"\nSample size: n = {n_samples}")
    print(f"Sample mean: {np.mean(data):.6f}")
    print(f"Sample std: {np.std(data):.6f}")
    print(f"Sample CV: {np.std(data)/np.mean(data):.4f}")
    
    if n_samples < 30:
        print("WARNING: Sample size too small for reliable parameter estimation!")
        return None
    
    # Fit both distributions
    print("\n" + "-"*80)
    print("MODEL 1: Exponential Distribution (k = 1)")
    print("-"*80)
    exp_result = fit_exponential(data)
    print(f"  τ̄ (scale) = {exp_result['tau_bar']:.6f}")
    print(f"  Mean = {exp_result['mean']:.6f}")
    print(f"  Variance = {exp_result['variance']:.6f}")
    print(f"  Log-likelihood = {exp_result['log_likelihood']:.2f}")
    print(f"  KS test: stat = {exp_result['ks_stat']:.4f}, p = {exp_result['ks_p']:.4f}")
    
    print("\n" + "-"*80)
    print("MODEL 2: Gamma Distribution (k free)")
    print("-"*80)
    gamma_result = fit_gamma(data)
    print(f"  k (shape) = {gamma_result['k']:.4f}")
    print(f"  θ (scale) = {gamma_result['theta']:.6f}")
    print(f"  Mean = k·θ = {gamma_result['mean']:.6f}")
    print(f"  Variance = k·θ² = {gamma_result['variance']:.6f}")
    print(f"  Log-likelihood = {gamma_result['log_likelihood']:.2f}")
    print(f"  KS test: stat = {gamma_result['ks_stat']:.4f}, p = {gamma_result['ks_p']:.4f}")
    print(f"  Optimization: {'✓ Converged' if gamma_result['optimization_success'] else '✗ Failed'}")
    
    # Likelihood ratio test
    print("\n" + "-"*80)
    print("LIKELIHOOD RATIO TEST: H0: k=1 (Exponential) vs H1: k≠1 (Gamma)")
    print("-"*80)
    lr_result = likelihood_ratio_test(exp_result, gamma_result, n_samples)
    print(f"  LR statistic = {lr_result['lr_statistic']:.4f}")
    print(f"  Degrees of freedom = {lr_result['df']}")
    print(f"  p-value = {lr_result['p_value']:.6f}")
    
    if lr_result['significant_05']:
        print(f"  ✓ REJECT H0 at α=0.05: Gamma is significantly better than Exponential")
        print(f"    → k = {gamma_result['k']:.3f} is significantly different from 1")
    else:
        print(f"  ✗ FAIL TO REJECT H0 at α=0.05: Cannot distinguish from Exponential")
        print(f"    → k = {gamma_result['k']:.3f} not significantly different from 1")
    
    # Information criteria
    print("\n" + "-"*80)
    print("INFORMATION CRITERIA (lower is better)")
    print("-"*80)
    exp_ic = compute_information_criteria(exp_result, n_samples)
    gamma_ic = compute_information_criteria(gamma_result, n_samples)
    
    print(f"  {'Model':<15} {'AIC':<15} {'BIC':<15}")
    print(f"  {'Exponential':<15} {exp_ic['AIC']:<15.2f} {exp_ic['BIC']:<15.2f}")
    print(f"  {'Gamma':<15} {gamma_ic['AIC']:<15.2f} {gamma_ic['BIC']:<15.2f}")
    print(f"  {'Difference':<15} {gamma_ic['AIC']-exp_ic['AIC']:<15.2f} {gamma_ic['BIC']-exp_ic['BIC']:<15.2f}")
    
    # Delta AIC interpretation
    delta_aic = gamma_ic['AIC'] - exp_ic['AIC']
    if delta_aic < -10:
        print(f"  → Gamma MUCH better (ΔAIC = {delta_aic:.1f} < -10)")
    elif delta_aic < -2:
        print(f"  → Gamma better (ΔAIC = {delta_aic:.1f} < -2)")
    elif delta_aic < 2:
        print(f"  → Models equivalent (|ΔAIC| = {abs(delta_aic):.1f} < 2)")
    else:
        print(f"  → Exponential better (ΔAIC = {delta_aic:.1f} > 2)")
    
    # Visualizations
    plot_comparison(data, exp_result, gamma_result, test_label)
    
    return {
        'data': data,
        'exp_result': exp_result,
        'gamma_result': gamma_result,
        'lr_test': lr_result,
        'exp_ic': exp_ic,
        'gamma_ic': gamma_ic,
        'test_label': test_label
    }


def plot_comparison(data, exp_result, gamma_result, test_label):
    """Create comprehensive comparison plots."""
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
    
    # 1. Histogram with PDFs
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.hist(data, bins=40, density=True, alpha=0.6, color='lightblue', 
             edgecolor='black', label='Empirical')
    
    x_plot = np.linspace(0, data.max(), 300)
    
    # Exponential PDF
    y_exp = (1/exp_result['tau_bar']) * np.exp(-x_plot/exp_result['tau_bar'])
    ax1.plot(x_plot, y_exp, 'r-', linewidth=2, 
             label=f'Exponential (τ={exp_result["tau_bar"]:.3f})')
    
    # Gamma PDF
    y_gamma = sp_stats.gamma.pdf(x_plot, gamma_result['k'], scale=gamma_result['theta'])
    ax1.plot(x_plot, y_gamma, 'g-', linewidth=2,
             label=f'Gamma (k={gamma_result["k"]:.3f}, θ={gamma_result["theta"]:.3f})')
    
    ax1.set_xlabel('Residence Time', fontsize=11)
    ax1.set_ylabel('Probability Density', fontsize=11)
    ax1.set_title(f'PDF Comparison\n{test_label}', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Q-Q plot: Exponential
    ax2 = fig.add_subplot(gs[0, 1])
    sorted_data = np.sort(data)
    theoretical_exp = sp_stats.expon.ppf(
        np.linspace(0.01, 0.99, len(sorted_data)), 
        scale=exp_result['tau_bar']
    )
    ax2.scatter(theoretical_exp, sorted_data, alpha=0.4, s=10, color='red')
    lims = [0, max(theoretical_exp.max(), sorted_data.max())]
    ax2.plot(lims, lims, 'k--', linewidth=2, label='Perfect fit')
    ax2.set_xlabel('Theoretical Exponential Quantiles', fontsize=11)
    ax2.set_ylabel('Sample Quantiles', fontsize=11)
    ax2.set_title(f'Q-Q Plot: Exponential\nKS = {exp_result["ks_stat"]:.4f}', 
                  fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. Q-Q plot: Gamma
    ax3 = fig.add_subplot(gs[0, 2])
    theoretical_gamma = sp_stats.gamma.ppf(
        np.linspace(0.01, 0.99, len(sorted_data)),
        gamma_result['k'], scale=gamma_result['theta']
    )
    ax3.scatter(theoretical_gamma, sorted_data, alpha=0.4, s=10, color='green')
    lims = [0, max(theoretical_gamma.max(), sorted_data.max())]
    ax3.plot(lims, lims, 'k--', linewidth=2, label='Perfect fit')
    ax3.set_xlabel('Theoretical Gamma Quantiles', fontsize=11)
    ax3.set_ylabel('Sample Quantiles', fontsize=11)
    ax3.set_title(f'Q-Q Plot: Gamma\nKS = {gamma_result["ks_stat"]:.4f}', 
                  fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. CDF comparison
    ax4 = fig.add_subplot(gs[1, 0])
    x_cdf = np.sort(data)
    y_empirical = np.arange(1, len(x_cdf)+1) / len(x_cdf)
    
    ax4.plot(x_cdf, y_empirical, 'o', markersize=3, alpha=0.5, label='Empirical')
    ax4.plot(x_plot, sp_stats.expon.cdf(x_plot, scale=exp_result['tau_bar']),
             'r-', linewidth=2, label='Exponential')
    ax4.plot(x_plot, sp_stats.gamma.cdf(x_plot, gamma_result['k'], scale=gamma_result['theta']),
             'g-', linewidth=2, label='Gamma')
    
    ax4.set_xlabel('Residence Time', fontsize=11)
    ax4.set_ylabel('Cumulative Probability', fontsize=11)
    ax4.set_title('CDF Comparison', fontsize=12, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 5. Residuals: Exponential
    ax5 = fig.add_subplot(gs[1, 1])
    residuals_exp = y_empirical - sp_stats.expon.cdf(x_cdf, scale=exp_result['tau_bar'])
    ax5.scatter(x_cdf, residuals_exp, alpha=0.4, s=10, color='red')
    ax5.axhline(0, color='black', linestyle='--', linewidth=1)
    ax5.set_xlabel('Residence Time', fontsize=11)
    ax5.set_ylabel('CDF Residual', fontsize=11)
    ax5.set_title('Residuals: Exponential', fontsize=12, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    
    # 6. Residuals: Gamma
    ax6 = fig.add_subplot(gs[1, 2])
    residuals_gamma = y_empirical - sp_stats.gamma.cdf(x_cdf, gamma_result['k'], scale=gamma_result['theta'])
    ax6.scatter(x_cdf, residuals_gamma, alpha=0.4, s=10, color='green')
    ax6.axhline(0, color='black', linestyle='--', linewidth=1)
    ax6.set_xlabel('Residence Time', fontsize=11)
    ax6.set_ylabel('CDF Residual', fontsize=11)
    ax6.set_title('Residuals: Gamma', fontsize=12, fontweight='bold')
    ax6.grid(True, alpha=0.3)
    
    plt.suptitle(f'Gamma vs Exponential Residence Time Distribution\n{test_label}',
                 fontsize=14, fontweight='bold')
    
    # Save
    filename = f'gamma_vs_exponential_{"_".join(test_label.lower().split())}.png'
    plt.savefig(molass_path / 'study' / filename, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: study/{filename}")


def main(num_frames=400, seed=42, test_mode='separate'):
    """Run complete Gamma vs Exponential comparison."""
    # Run animation
    stats = run_animation_with_tracking(num_frames=num_frames, seed=seed)
    
    type_names = ['Large (green)', 'Medium (blue)', 'Small (red)']
    
    if test_mode in ['combined', 'both']:
        print("\n" + "="*80)
        print("COMBINED MODE (All particles together)")
        print("="*80)
        result = test_gamma_vs_exponential(stats, particle_type=None)
    
    if test_mode in ['separate', 'both']:
        print("\n" + "="*80)
        print("SEPARATE MODE (Each species tested individually)")
        print("="*80)
        
        results = []
        for ptype in range(3):
            result = test_gamma_vs_exponential(stats, particle_type=ptype)
            results.append(result)
        
        # Summary table
        print("\n" + "="*80)
        print("SUMMARY: Gamma Shape Parameter by Particle Type")
        print("="*80)
        print(f"{'Type':<15} {'k (shape)':<12} {'k=1?':<10} {'p-value':<12} {'ΔAIC':<10} {'Conclusion':<20}")
        print("-" * 80)
        
        for ptype, result in enumerate(results):
            if result is None:
                continue
            
            k_val = result['gamma_result']['k']
            lr_p = result['lr_test']['p_value']
            is_one = "Yes" if lr_p >= 0.05 else "No"
            delta_aic = result['gamma_ic']['AIC'] - result['exp_ic']['AIC']
            
            if delta_aic < -2:
                conclusion = "Gamma better"
            elif delta_aic < 2:
                conclusion = "Equivalent"
            else:
                conclusion = "Exponential better"
            
            print(f"{type_names[ptype]:<15} {k_val:<12.4f} {is_one:<10} {lr_p:<12.6f} {delta_aic:<10.2f} {conclusion:<20}")
        
        print("\n" + "="*80)
        print("INTERPRETATION")
        print("="*80)
        print("k < 1: Heavy-tailed → some molecules trapped for long times")
        print("k = 1: Exponential → standard GEC assumption (memoryless)")
        print("k > 1: More uniform → tighter distribution of residence times")
        print("\nIf k ≈ 1 for all species → Exponential assumption is valid")
        print("If k significantly ≠ 1 → Consider Gamma model for better accuracy")
    
    plt.show()
    return results if test_mode == 'separate' else result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Test Gamma vs Exponential residence times')
    parser.add_argument('--frames', type=int, default=400,
                        help='Number of animation frames (default: 400)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed (default: 42)')
    parser.add_argument('--mode', choices=['combined', 'separate', 'both'],
                        default='separate',
                        help='Test mode (default: separate)')
    args = parser.parse_args()
    
    main(num_frames=args.frames, seed=args.seed, test_mode=args.mode)
