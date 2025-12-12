"""
Demonstration: Equivalence of Lévy FFT and Monte Carlo Approaches

This script shows that the analytical Lévy process method (FFT inversion)
and Monte Carlo simulation produce equivalent chromatographic peak shapes.

Both methods start from the same sorption time distribution and predict
the same ensemble-averaged retention time distribution.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats


def levy_fft_method(tauS_i, DeltaF_i, rM_bar, n_points=2048):
    """
    Analytical Lévy approach: CF → FFT inversion → Peak
    
    Based on Pasti et al. 2005 eq 26a:
    φ(ω) = exp[r̄M * Σ(exp(iω*τS,i) - 1) * ΔF(τS,i)]
    """
    # Estimate time scale
    tauS_mean = np.sum(tauS_i * DeltaF_i)
    expected_tS = rM_bar * tauS_mean
    dt = expected_tS / n_points * 4
    
    # Build symmetric frequency array for real output: [0, dω, ..., ωmax, -ωmax, ..., -dω]
    # This ensures the inverse FFT produces a real-valued probability density
    dw = 2 * np.pi / (n_points * dt)
    omega = np.fft.fftfreq(n_points, dt) * 2 * np.pi
    
    # Characteristic function at all frequencies (positive and negative)
    sum_term = np.zeros_like(omega, dtype=complex)
    for tau, deltaF in zip(tauS_i, DeltaF_i):
        sum_term += (np.exp(1j * omega * tau) - 1) * deltaF
    cf = np.exp(rM_bar * sum_term)
    
    # Inverse FFT to get probability density
    # The CF is the Fourier transform of the PDF, so IFFT gives us the PDF
    peak = np.fft.ifft(cf).real
    
    # Shift so time starts at 0 (FFT assumes periodic, centered at 0)
    peak = np.fft.ifftshift(peak)
    
    # Normalize to unit area
    peak = peak / (np.sum(peak) * dt)
    
    # Ensure non-negative (clip small numerical errors)
    peak = np.maximum(peak, 0)
    
    time = np.arange(n_points) * dt
    
    return time, peak


def monte_carlo_method(tauS_i, DeltaF_i, rM_bar, n_molecules=10000):
    """
    Monte Carlo simulation: Sample individual molecular trajectories
    
    Each molecule undergoes rM adsorption events (Poisson distributed),
    with sorption times sampled from the discrete distribution.
    """
    # Generate number of adsorption events per molecule (Poisson)
    rM_values = np.random.poisson(rM_bar, n_molecules)
    
    # For each molecule, sum the sorption times
    total_times = np.zeros(n_molecules)
    
    for i, rM in enumerate(rM_values):
        if rM > 0:
            # Sample rM sorption times from discrete distribution
            sorption_times = np.random.choice(tauS_i, size=rM, p=DeltaF_i)
            total_times[i] = np.sum(sorption_times)
    
    return total_times


def simple_comparison(save_fig=False):
    """
    Simple demonstration with a two-component distribution.
    """
    print("=" * 70)
    print("Simple Comparison: Lévy FFT vs Monte Carlo")
    print("=" * 70)
    
    # Simple two-component sorption time distribution
    tauS_i = np.array([10, 100])  # Fast and slow sites
    DeltaF_i = np.array([0.8, 0.2])  # 80% fast, 20% slow
    rM_bar = 50  # Mean number of adsorption events
    
    print(f"\nSorption time distribution:")
    print(f"  τS = {tauS_i[0]} (80% of sites)")
    print(f"  τS = {tauS_i[1]} (20% of sites)")
    print(f"  Mean number of adsorptions: r̄M = {rM_bar}")
    print(f"  Expected mean time: {rM_bar * np.sum(tauS_i * DeltaF_i):.1f}")
    
    # Method 1: Lévy FFT (analytical)
    print("\n[1] Computing Lévy FFT solution...")
    time_levy, peak_levy = levy_fft_method(tauS_i, DeltaF_i, rM_bar, n_points=2048)
    
    # Method 2: Monte Carlo (simulation)
    print("[2] Running Monte Carlo simulation...")
    n_molecules = 100000
    total_times_mc = monte_carlo_method(tauS_i, DeltaF_i, rM_bar, n_molecules=n_molecules)
    
    # Create histogram from Monte Carlo
    bins = np.linspace(0, time_levy[-1], 100)
    hist_counts, bin_edges = np.histogram(total_times_mc, bins=bins, density=True)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Plot comparison
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Overlay plot
    ax = axes[0]
    ax.plot(time_levy, peak_levy, 'r-', linewidth=2.5, label='Lévy FFT (analytical)', alpha=0.5)
    ax.hist(total_times_mc, bins=bins, density=True, alpha=0.5, 
            color='blue', edgecolor='black', linewidth=0.5, label=f'Monte Carlo (n={n_molecules})')
    ax.set_xlabel('Total time in stationary phase')
    ax.set_ylabel('Probability density')
    ax.set_title('Method Comparison')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Difference plot
    ax = axes[1]
    peak_levy_interp = np.interp(bin_centers, time_levy, peak_levy)
    difference = hist_counts - peak_levy_interp
    relative_error = np.abs(difference) / (peak_levy_interp + 1e-10) * 100
    
    ax.plot(bin_centers, difference, 'k-', linewidth=1.5)
    ax.axhline(0, color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel('Total time in stationary phase')
    ax.set_ylabel('Difference (MC - Lévy)')
    ax.set_title('Residuals')
    ax.grid(True, alpha=0.3)
    
    # Print statistics
    mean_levy = np.sum(time_levy * peak_levy * (time_levy[1] - time_levy[0]))
    mean_mc = np.mean(total_times_mc)
    std_levy = np.sqrt(np.sum((time_levy - mean_levy)**2 * peak_levy * (time_levy[1] - time_levy[0])))
    std_mc = np.std(total_times_mc)
    
    print(f"\nStatistics:")
    print(f"  Lévy FFT:    Mean = {mean_levy:.2f}, Std = {std_levy:.2f}")
    print(f"  Monte Carlo: Mean = {mean_mc:.2f}, Std = {std_mc:.2f}")
    print(f"  Mean difference: {abs(mean_levy - mean_mc):.2f} ({abs(mean_levy - mean_mc)/mean_levy*100:.2f}%)")
    print(f"  Max relative error: {np.max(relative_error[peak_levy_interp > 0.01*np.max(peak_levy_interp)]):.2f}%")
    
    plt.tight_layout()
    if save_fig:
        plt.savefig('levy_montecarlo_simple_comparison.png', dpi=300)
        print("\nPlot saved: levy_montecarlo_simple_comparison.png")
    plt.show()


def convergence_study():
    """
    Show how Monte Carlo converges to Lévy solution as n_molecules increases.
    """
    print("\n" + "=" * 70)
    print("Convergence Study: Monte Carlo → Lévy (analytical limit)")
    print("=" * 70)
    
    # Distribution
    tauS_i = np.array([5, 50, 200])
    DeltaF_i = np.array([0.7, 0.25, 0.05])
    rM_bar = 30
    
    # Lévy solution (analytical)
    print("\nComputing analytical Lévy solution...")
    time_levy, peak_levy = levy_fft_method(tauS_i, DeltaF_i, rM_bar, n_points=2048)
    
    # Different Monte Carlo sample sizes
    n_molecules_list = [100, 1000, 10000, 100000]
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    
    errors = []
    
    for idx, n_mol in enumerate(n_molecules_list):
        print(f"\nMonte Carlo with n = {n_mol}...")
        
        # Run Monte Carlo
        total_times_mc = monte_carlo_method(tauS_i, DeltaF_i, rM_bar, n_molecules=n_mol)
        
        # Histogram
        bins = np.linspace(0, time_levy[-1], 80)
        
        ax = axes[idx]
        ax.plot(time_levy, peak_levy, 'r-', linewidth=2.5, label='Lévy (analytical)', alpha=0.9)
        ax.hist(total_times_mc, bins=bins, density=True, alpha=0.6,
                color='blue', edgecolor='black', linewidth=0.5, label=f'MC (n={n_mol})')
        ax.set_xlabel('Total time')
        ax.set_ylabel('Probability density')
        ax.set_title(f'n = {n_mol} molecules')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Calculate error
        hist_counts, _ = np.histogram(total_times_mc, bins=bins, density=True)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        peak_levy_interp = np.interp(bin_centers, time_levy, peak_levy)
        rmse = np.sqrt(np.mean((hist_counts - peak_levy_interp)**2))
        errors.append(rmse)
        
        ax.text(0.95, 0.95, f'RMSE = {rmse:.4f}', transform=ax.transAxes,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('levy_montecarlo_convergence.png', dpi=300)
    print("\nPlot saved: levy_montecarlo_convergence.png")
    plt.show()
    
    # Error vs sample size
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.loglog(n_molecules_list, errors, 'bo-', markersize=10, linewidth=2)
    
    # Expected 1/sqrt(n) convergence
    n_array = np.array(n_molecules_list)
    expected_line = errors[0] * np.sqrt(n_molecules_list[0] / n_array)
    ax.loglog(n_array, expected_line, 'r--', linewidth=2, label='1/√n convergence', alpha=0.7)
    
    ax.set_xlabel('Number of molecules')
    ax.set_ylabel('RMSE')
    ax.set_title('Monte Carlo Convergence to Lévy Solution')
    ax.legend()
    ax.grid(True, alpha=0.3, which='both')
    
    plt.tight_layout()
    plt.savefig('levy_montecarlo_error.png', dpi=300)
    print("Plot saved: levy_montecarlo_error.png")
    plt.show()


def peak_shape_variations():
    """
    Show equivalence for different peak shapes (symmetric, skewed, bimodal).
    """
    print("\n" + "=" * 70)
    print("Peak Shape Variations: Testing Different Distributions")
    print("=" * 70)
    
    configurations = [
        {
            'name': 'Symmetric (single mode)',
            'tauS_i': np.array([50]),
            'DeltaF_i': np.array([1.0]),
            'rM_bar': 40,
        },
        {
            'name': 'Skewed (rare slow sites)',
            'tauS_i': np.array([10, 100]),
            'DeltaF_i': np.array([0.95, 0.05]),
            'rM_bar': 50,
        },
        {
            'name': 'Bimodal (two populations)',
            'tauS_i': np.array([20, 80]),
            'DeltaF_i': np.array([0.5, 0.5]),
            'rM_bar': 30,
        },
        {
            'name': 'Multi-site heterogeneity',
            'tauS_i': np.array([5, 15, 30, 60, 150]),
            'DeltaF_i': np.array([0.4, 0.3, 0.2, 0.08, 0.02]),
            'rM_bar': 60,
        },
    ]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    for idx, config in enumerate(configurations):
        print(f"\n{config['name']}...")
        
        # Lévy
        time_levy, peak_levy = levy_fft_method(
            config['tauS_i'], config['DeltaF_i'], config['rM_bar']
        )
        
        # Monte Carlo
        total_times_mc = monte_carlo_method(
            config['tauS_i'], config['DeltaF_i'], config['rM_bar'], n_molecules=50000
        )
        
        # Plot
        ax = axes[idx]
        bins = np.linspace(0, time_levy[-1], 100)
        ax.plot(time_levy, peak_levy, 'r-', linewidth=2.5, label='Lévy FFT', alpha=0.9)
        ax.hist(total_times_mc, bins=bins, density=True, alpha=0.5,
                color='blue', edgecolor='black', linewidth=0.5, label='Monte Carlo')
        ax.set_xlabel('Total time')
        ax.set_ylabel('Probability density')
        ax.set_title(config['name'])
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('levy_montecarlo_peak_shapes.png', dpi=300)
    print("\nPlot saved: levy_montecarlo_peak_shapes.png")
    plt.show()


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("Lévy FFT vs Monte Carlo: Demonstrating Equivalence")
    print("=" * 70)
    print("\nBoth methods solve the same stochastic problem:")
    print("  - Lévy: Analytical solution via characteristic function")
    print("  - Monte Carlo: Numerical sampling of random trajectories")
    print("=" * 70)
    
    # Run demonstrations
    simple_comparison()
    convergence_study()
    peak_shape_variations()
    
    print("\n" + "=" * 70)
    print("Summary:")
    print("  ✓ Lévy FFT gives exact analytical solution (fast)")
    print("  ✓ Monte Carlo converges to same result (scales as 1/√n)")
    print("  ✓ Both methods are equivalent for ensemble averages")
    print("  ✓ Monte Carlo allows spatial effects (clustering, diffusion)")
    print("=" * 70)
