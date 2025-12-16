"""
Lévy Process Chromatography Peak Calculation (Pasti et al. 2005)

Python implementation of the Mathematica code from Figure 2 of:
"Single-Molecule Observation and Chromatography Unified by Lévy Process Representation"
Pasti, L.; Cavazzini, A.; Felinger, A.; Martin, M.; Dondi, F.
Anal. Chem. 2005, 77, 8, 2524-2535

This code inverts the characteristic function (CF) using FFT to obtain
the chromatographic peak from discrete sorption time distributions.
"""

import numpy as np
import matplotlib.pyplot as plt


def levy_cf_discrete(omega, tauS_i, DeltaF_i, rM_bar):
    """
    Calculate the characteristic function for discrete sorption times.
    
    This implements eq 26a from Pasti 2005:
    φ(ω|tM) = exp[r̄M * Σ(exp(iω*τS,i) - 1) * ΔF(τS,i)]
    
    Parameters
    ----------
    omega : ndarray
        Frequency array (rad/time)
    tauS_i : ndarray
        Discrete sorption time values (time units)
    DeltaF_i : ndarray
        Frequency (probability) of each sorption time
    rM_bar : float
        Mean number of adsorption events during column transit
    
    Returns
    -------
    cf : ndarray (complex)
        Characteristic function values
    """
    # Sum over all discrete sorption times
    sum_term = np.zeros_like(omega, dtype=complex)
    for tau, deltaF in zip(tauS_i, DeltaF_i):
        sum_term += (np.exp(1j * omega * tau) - 1) * deltaF
    
    # Characteristic function
    cf = np.exp(rM_bar * sum_term)
    return cf


def invert_cf_fft(cf, dt):
    """
    Invert the characteristic function using FFT to get the peak in time domain.
    
    Note: The characteristic function convention φ(ω) = E[exp(+iωt)] differs from
    NumPy's FFT convention (exp(-iωt)), so we use the conjugate.
    
    For long retention times, FFT periodicity may cause peaks to wrap in the array.
    This affects absolute time positioning but not peak shapes or relative separations.
    
    Parameters
    ----------
    cf : ndarray (complex)
        Characteristic function values at symmetric frequencies from fftfreq
    dt : float
        Time increment
    
    Returns
    -------
    time : ndarray
        Time values starting at 0
    peak : ndarray
        Chromatographic peak (probability density)
    """
    # Use conjugate to match CF convention: φ(ω) = E[exp(+iωt)]
    peak = np.fft.ifft(np.conj(cf)).real
    
    # Normalize to unit area
    peak = peak / (np.sum(peak) * dt)
    
    # Ensure non-negative (clip small numerical errors)  
    peak = np.maximum(peak, 0)
    
    # Time axis starts at 0
    time = np.arange(len(peak)) * dt
    
    return time, peak


def calculate_chromatographic_peak(tauS_i, DeltaF_i, rM_bar, tM=0, n_points=2048):
    """
    Calculate the chromatographic peak from discrete sorption time distribution.
    
    Parameters
    ----------
    tauS_i : array-like
        Discrete sorption time values
    DeltaF_i : array-like
        Probability of each sorption time (must sum to 1)
    rM_bar : float
        Mean number of adsorption-desorption events
    tM : float, optional
        Mean time in mobile phase (for retention time shift)
    n_points : int, optional
        Number of points for FFT (power of 2 recommended)
    
    Returns
    -------
    time : ndarray
        Time values (stationary phase time)
    peak : ndarray
        Chromatographic peak shape f(tS)
    retention_time : ndarray
        Total retention time (tR = tM + tS)
    retention_peak : ndarray
        Peak in retention time domain
    """
    # Convert to numpy arrays
    tauS_i = np.array(tauS_i)
    DeltaF_i = np.array(DeltaF_i)
    
    # Validate inputs
    if len(tauS_i) != len(DeltaF_i):
        raise ValueError("tauS_i and DeltaF_i must have same length")
    
    if not np.isclose(np.sum(DeltaF_i), 1.0):
        print(f"Warning: DeltaF_i sums to {np.sum(DeltaF_i):.4f}, normalizing...")
        DeltaF_i = DeltaF_i / np.sum(DeltaF_i)
    
    # Calculate mean sorption time for time scale estimation
    tauS_mean = np.sum(tauS_i * DeltaF_i)
    expected_tS = rM_bar * tauS_mean
    
    # Set up frequency domain with symmetric frequencies
    # Time increment: small enough to resolve the peak
    dt = expected_tS / n_points * 4  # 4x expected time range
    
    # Build symmetric frequency array: [0, dω, ..., ωmax, -ωmax, ..., -dω]
    omega = np.fft.fftfreq(n_points, dt) * 2 * np.pi
    
    # Calculate characteristic function at all frequencies (positive and negative)
    cf = levy_cf_discrete(omega, tauS_i, DeltaF_i, rM_bar)
    
    # Invert to time domain
    time, peak = invert_cf_fft(cf, dt)
    
    # Add mobile phase time for total retention time
    retention_time = time + tM
    retention_peak = peak.copy()
    
    return time, peak, retention_time, retention_peak


def example_case_A():
    """
    Example: Case A from Pasti 2005 Table 1
    λ-DNA adsorption on fused silica (from ref 1, Figure 7)
    """
    print("=" * 70)
    print("Case A: λ-DNA on fused silica (Pasti 2005, Table 1)")
    print("=" * 70)
    
    # Data from Table 1, Case A (Figure 7 ref 1)
    tauS_i = np.array([33.3, 66.7, 100, 133.3, 167.7, 200, 267])  # ms
    DeltaF_i = np.array([0.0263, 0.4211, 0.3421, 0.1053, 0.0526, 0.0263, 0.0263])
    
    # Mean sorption time
    tauS_mean = np.sum(tauS_i * DeltaF_i)
    print(f"\nMean sorption time τ̄S = {tauS_mean:.1f} ms")
    
    # Simulation parameters
    tM = 0.1 * 60 * 1000  # 0.1 min converted to ms
    
    # Different rM values to explore peak splitting
    rM_values = [3, 5, 15, 100, 812]
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    
    for idx, rM_bar in enumerate(rM_values):
        if idx >= len(axes):
            break
            
        print(f"\nCalculating peak for r̄M = {rM_bar}...")
        
        # Calculate peak
        time, peak, ret_time, ret_peak = calculate_chromatographic_peak(
            tauS_i, DeltaF_i, rM_bar, tM=tM, n_points=4096
        )
        
        # Convert to minutes for plotting
        ret_time_min = ret_time / (60 * 1000)
        
        # Expected retention time
        tR_expected = tM + rM_bar * tauS_mean
        tR_expected_min = tR_expected / (60 * 1000)
        
        # Plot
        ax = axes[idx]
        ax.plot(ret_time_min, ret_peak, 'b-', linewidth=2)
        ax.axvline(tR_expected_min, color='r', linestyle='--', alpha=0.5, 
                   label=f'Expected: {tR_expected_min:.3f} min')
        ax.set_xlabel('Retention time (min)')
        ax.set_ylabel('f(tR)')
        ax.set_title(f'r̄M = {rM_bar}')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Show peak splitting for low rM
        if rM_bar <= 15:
            # Fraction never adsorbed
            f_never = np.exp(-rM_bar)
            ax.text(0.05, 0.95, f'Never ads.: {f_never:.1%}', 
                   transform=ax.transAxes, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Remove empty subplot
    if len(rM_values) < len(axes):
        fig.delaxes(axes[-1])
    
    plt.tight_layout()
    plt.savefig('pasti2005_case_A_peaks.png', dpi=300)
    print("\nPlot saved: pasti2005_case_A_peaks.png")
    plt.show()


def example_case_B():
    """
    Example: Case B from Pasti 2005 Table 1
    DiI dye on C18 surface (from ref 2, Figure 8)
    With NS (nonspecific) + S (specific) contributions
    
    Uses characteristic function multiplication: φ_combined = φ_NS × φ_S
    This is the correct way to combine two independent adsorption processes.
    """
    print("\n" + "=" * 70)
    print("Case B: DiI on C18 with NS + S sites (Pasti 2005, Table 1)")
    print("=" * 70)
    
    # Specific (S) sites - discrete distribution
    tauS_i_S = np.array([160, 320, 480, 640, 800, 2240, 2720, 3360])  # ms
    DeltaF_S = np.array([0.2778, 0.1111, 0.1111, 0.2778, 0.05555, 
                         0.05555, 0.05555, 0.05555])
    
    # Nonspecific (NS) sites - exponential distribution (single value)
    tauS_i_NS = np.array([68])  # ms
    DeltaF_NS = np.array([1.0])
    
    # Parameters
    p = 0.01  # fraction of specific sites
    rM_total = 1000
    rM_S = int(p * rM_total)
    rM_NS = rM_total - rM_S
    
    tauS_mean_S = np.sum(tauS_i_S * DeltaF_S)
    tauS_mean_NS = tauS_i_NS[0]
    
    print(f"\nNonspecific sites: τ̄S,NS = {tauS_mean_NS:.1f} ms, r̄M,NS = {rM_NS}")
    print(f"Specific sites: τ̄S,S = {tauS_mean_S:.1f} ms, r̄M,S = {rM_S}")
    print(f"Combined mean: {rM_NS * tauS_mean_NS + rM_S * tauS_mean_S:.1f} ms")
    
    # Estimate total time range for combined system
    total_mean = rM_NS * tauS_mean_NS + rM_S * tauS_mean_S
    
    # Setup common frequency domain for all calculations
    n_points = 8192  # Higher resolution for better accuracy
    dt = total_mean / n_points * 6  # Cover wider range
    omega = np.fft.fftfreq(n_points, dt) * 2 * np.pi
    
    # Calculate characteristic functions
    cf_NS = levy_cf_discrete(omega, tauS_i_NS, DeltaF_NS, rM_NS)
    cf_S = levy_cf_discrete(omega, tauS_i_S, DeltaF_S, rM_S)
    
    # Combined CF = product of independent processes
    cf_combined = cf_NS * cf_S
    
    # Invert all three CFs to time domain
    time_NS, peak_NS = invert_cf_fft(cf_NS, dt)
    time_S, peak_S = invert_cf_fft(cf_S, dt)
    time_combined, peak_combined = invert_cf_fft(cf_combined, dt)
    
    # Plot single comprehensive figure
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    
    # Add mobile phase time for retention time
    tM = 30 * 1000  # 30 seconds (much longer for visibility)
    
    # Plot all three peaks
    ax.plot((time_combined + tM) / 1000, peak_combined, 'k-', linewidth=2.5, label='NS + S (combined)')
    ax.plot((time_NS + tM) / 1000, peak_NS, 'b--', linewidth=2, label='NS only', alpha=0.7)
    ax.plot((time_S + tM) / 1000, peak_S, 'r--', linewidth=2, label='S only', alpha=0.7)
    
    # Add shaded region to show mobile phase contribution
    ax.axvspan(0, tM / 1000, alpha=0.1, color='gray', label=f'Mobile phase (tM = {tM/1000:.0f} s)')
    
    ax.set_xlabel('Retention time (s)')
    ax.set_ylabel('Probability density f(tR)')
    ax.set_title('DiI Dye Chromatographic Peaks (NS + S binding sites)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Add comprehensive statistics
    textstr = '\n'.join([
        f'tM = {tM/1000:.0f} s',
        f'NS: {rM_NS} events × {tauS_mean_NS:.0f} ms → tR = {(tM + rM_NS * tauS_mean_NS)/1000:.1f} s',
        f'S: {rM_S} events × {tauS_mean_S:.0f} ms → tR = {(tM + rM_S * tauS_mean_S)/1000:.1f} s',
        f'Combined: tR = {(tM + total_mean)/1000:.1f} s'
    ])
    ax.text(0.98, 0.97, textstr, transform=ax.transAxes,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
            fontsize=9)
    
    plt.tight_layout()
    plt.savefig('pasti2005_case_B_peak.png', dpi=300)
    print("\nPlot saved: pasti2005_case_B_peak.png")
    plt.show()


def compare_with_monte_carlo():
    """
    Compare Lévy FFT approach with Monte Carlo simulation results.
    Uses parameters similar to your repository code.
    """
    print("\n" + "=" * 70)
    print("Comparison: Lévy FFT vs Monte Carlo (your repository)")
    print("=" * 70)
    
    # Parameters from your script_column_run.py
    tau_des0 = 10  # μs
    ts1 = tau_des0
    ts2 = 50 * ts1  # 500 μs for rare sites
    
    # Create discrete distribution: 98% fast, 2% slow
    tauS_i = np.array([ts1, ts2])
    DeltaF_i = np.array([0.98, 0.02])
    
    # Column parameters
    L = 2000  # μm
    vm = 0.2  # μm/μs
    tM = L / vm  # 10,000 μs
    
    # Estimate rM_bar from your simulation parameters
    # ns = 4000 sites, lambda_ads = 1/10 μs^-1
    # Rough estimate: rM ~ few hundred to thousand
    rM_values = [100, 500, 1000]
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    for idx, rM_bar in enumerate(rM_values):
        print(f"\nCalculating for r̄M = {rM_bar}...")
        
        time, peak, ret_time, ret_peak = calculate_chromatographic_peak(
            tauS_i, DeltaF_i, rM_bar, tM=tM, n_points=2048
        )
        
        ax = axes[idx]
        ax.plot(ret_time, ret_peak, 'b-', linewidth=2)
        ax.set_xlabel('Retention time (μs)')
        ax.set_ylabel('Probability density')
        ax.set_title(f'r̄M = {rM_bar}')
        ax.grid(True, alpha=0.3)
        
        # Add statistics
        mean_ret = tM + rM_bar * np.sum(tauS_i * DeltaF_i)
        ax.axvline(mean_ret, color='r', linestyle='--', alpha=0.5,
                   label=f'Mean: {mean_ret:.0f} μs')
        ax.legend()
    
    plt.tight_layout()
    plt.savefig('levy_vs_montecarlo_comparison.png', dpi=300)
    print("\nPlot saved: levy_vs_montecarlo_comparison.png")
    print("\nNote: Compare this with histograms from your Monte Carlo simulation!")
    plt.show()


if __name__ == '__main__':
    print("Lévy Process Chromatography Peak Calculation")
    print("Based on Pasti et al. (2005) Anal. Chem.")
    print()
    
    # Run examples
    example_case_A()
    example_case_B()
    compare_with_monte_carlo()
    
    print("\n" + "=" * 70)
    print("Analysis complete!")
    print("=" * 70)
