"""
Visualize Single Particle Trajectory as a Lévy Process

This script creates a 3D animation showing how a single particle's trajectory
through the SEC column forms a Compound Poisson Process (a type of Lévy process).

The 3D visualization shows:
- X, Y axes: Spatial position in the column
- Z axis: Cumulative adsorbed time t_S(t) ← This is the Lévy process!

Key features:
- Horizontal segments: Particle is mobile (free diffusion, no time penalty)
- Vertical jumps: Particle is adsorbed (random "delays" accumulate)
- The result is a staircase-like 3D trajectory that visualizes the CPP structure

Usage:
    python visualize_levy_trajectory.py --particle 500 --frames 400
    python visualize_levy_trajectory.py --particle 1000 --type small
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
import argparse

# Add molass to path
molass_path = Path(__file__).parent.parent
sys.path.insert(0, str(molass_path))

from molass.SEC.ColumnSimulation import get_animation


def run_with_trajectory_tracking(particle_id, num_frames=400, seed=42):
    """
    Run animation and collect single particle trajectory.
    
    Parameters
    ----------
    particle_id : int
        Index of particle to track (0-indexed)
    num_frames : int
        Number of frames to simulate
    seed : int
        Random seed for reproducibility
    
    Returns
    -------
    trajectory_data : dict
        Dictionary containing trajectory information
    """
    print(f"Running animation with trajectory tracking...")
    print(f"  Particle ID: {particle_id}")
    print(f"  Frames: {num_frames}")
    print(f"  Seed: {seed}")
    
    anim, stats = get_animation(
        num_frames=num_frames,
        seed=seed,
        close_plot=True,
        track_particle_id=particle_id,
        use_tqdm=True,
        blit=False
    )
    
    # Execute all frames to collect trajectory data
    # Simply iterate through all frames without saving
    print("Executing animation frames to collect trajectory...")
    try:
        # Force execution by rendering each frame
        for i in range(num_frames):
            anim._func(i)
    except Exception as e:
        print(f"Note: Some frames may have had issues: {e}")
        print("Continuing with collected data...")
    
    print("Trajectory collection complete.")
    return stats['trajectory']


def create_3d_trajectory_plot(trajectory, output_path=None, interactive=True):
    """
    Create static 3D plot of the trajectory.
    
    Parameters
    ----------
    trajectory : dict
        Trajectory data from animation
    output_path : str or Path, optional
        If provided, save the plot to this path
    interactive : bool
        If True, show interactive plot
    """
    positions = trajectory['positions']
    states = trajectory['states']
    cum_time = trajectory['cumulative_adsorbed_time']
    particle_type = trajectory['particle_type']
    
    type_names = ['Large (green)', 'Medium (blue)', 'Small (red)']
    type_colors = ['green', 'blue', 'red']
    
    print(f"\nTrajectory Statistics:")
    print(f"  Particle type: {type_names[particle_type]}")
    print(f"  Total frames: {len(positions)}")
    print(f"  Final cumulative adsorbed time: {cum_time[-1]:.6f}")
    print(f"  Number of jumps (adsorption events): {np.sum(np.diff(cum_time) > 0)}")
    
    # Create 3D figure
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Extract coordinates
    # Remap: X=time (left to right), Y=horizontal position, Z=vertical position (top to bottom)
    x = cum_time         # Time flows left to right (Lévy process)
    y = positions[:, 0]  # Horizontal position in column
    z = positions[:, 1]  # Vertical position in column (particles fall downward)
    
    # Plot trajectory with color coding by state
    mobile_mask = states
    adsorbed_mask = ~states
    
    # Plot full trajectory
    ax.plot(x, y, z, 'k-', linewidth=0.5, alpha=0.3, label='Full trajectory')
    
    # Highlight adsorbed points (where time is increasing without much z movement)
    if np.any(adsorbed_mask):
        ax.scatter(x[adsorbed_mask], y[adsorbed_mask], z[adsorbed_mask], 
                  c='red', s=2, alpha=0.6, label='Adsorbed')
    
    # Highlight mobile points
    if np.any(mobile_mask):
        ax.scatter(x[mobile_mask], y[mobile_mask], z[mobile_mask], 
                  c='blue', s=2, alpha=0.4, label='Mobile')
    
    # Mark start and end
    ax.scatter([x[0]], [y[0]], [z[0]], c='lime', s=100, marker='o', 
              edgecolors='black', linewidths=2, label='Start (top)', zorder=10)
    ax.scatter([x[-1]], [y[-1]], [z[-1]], c='orange', s=100, marker='s', 
              edgecolors='black', linewidths=2, label='End (bottom)', zorder=10)
    
    # Labels and title
    ax.set_xlabel('Cumulative Adsorbed Time (Lévy Process)', fontsize=12)
    ax.set_ylabel('X Position (Horizontal)', fontsize=12)
    ax.set_zlabel('Y Position (Vertical, Top→Bottom)', fontsize=12)
    ax.set_title(f'3D Trajectory: {type_names[particle_type]} Particle\n'
                f'Compound Poisson Process - Particle Falls as Time Accumulates', 
                fontsize=14, fontweight='bold')
    
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Set viewing angle to see particles falling downward
    ax.view_init(elev=15, azim=-60)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nStatic plot saved to: {output_path}")
    
    if interactive:
        plt.show()
    else:
        plt.close()


def create_animated_trajectory(trajectory, output_path=None, fps=20):
    """
    Create animated 3D trajectory that builds frame-by-frame.
    
    Parameters
    ----------
    trajectory : dict
        Trajectory data from animation
    output_path : str or Path, optional
        If provided, save animation to this path
    fps : int
        Frames per second for animation
    """
    positions = trajectory['positions']
    states = trajectory['states']
    cum_time = trajectory['cumulative_adsorbed_time']
    particle_type = trajectory['particle_type']
    
    type_names = ['Large (green)', 'Medium (blue)', 'Small (red)']
    
    print(f"\nCreating animated 3D trajectory...")
    
    # Create figure
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')
    
    # Remap: X=time (left to right), Y=horizontal position, Z=vertical position
    x = cum_time         # Time (left to right)
    y = positions[:, 0]  # Horizontal position
    z = positions[:, 1]  # Vertical position (falls downward)
    
    # Initialize empty line and scatter objects
    line, = ax.plot([], [], [], 'k-', linewidth=1.5, alpha=0.7)
    scatter_mobile = ax.scatter([], [], [], c='blue', s=5, alpha=0.5)
    scatter_adsorbed = ax.scatter([], [], [], c='red', s=5, alpha=0.7)
    scatter_current = ax.scatter([], [], [], c='yellow', s=100, marker='o', 
                                edgecolors='black', linewidths=2, zorder=10)
    
    # Set axis limits
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(0, y.max() * 1.1)
    ax.set_zlim(z.min(), z.max())
    
    # Labels
    ax.set_xlabel('Cumulative Adsorbed Time', fontsize=11)
    ax.set_ylabel('X Position', fontsize=11)
    ax.set_zlabel('Y Position (Top→Bottom)', fontsize=11)
    
    title = ax.text2D(0.5, 0.95, '', transform=ax.transAxes, 
                     ha='center', fontsize=12, fontweight='bold')
    
    ax.view_init(elev=15, azim=-60)
    
    def init():
        line.set_data([], [])
        line.set_3d_properties([])
        return line, scatter_mobile, scatter_adsorbed, scatter_current, title
    
    def update(frame):
        # Slow down animation by showing every Nth frame
        i = min(frame * 2, len(x) - 1)  # Show every 2nd frame
        
        if i == 0:
            return line, scatter_mobile, scatter_adsorbed, scatter_current, title
        
        # Update trajectory line
        line.set_data(x[:i+1], y[:i+1])
        line.set_3d_properties(z[:i+1])
        
        # Update scatter points
        mobile_idx = np.where(states[:i+1])[0]
        adsorbed_idx = np.where(~states[:i+1])[0]
        
        if len(mobile_idx) > 0:
            scatter_mobile._offsets3d = (x[mobile_idx], y[mobile_idx], z[mobile_idx])
        if len(adsorbed_idx) > 0:
            scatter_adsorbed._offsets3d = (x[adsorbed_idx], y[adsorbed_idx], z[adsorbed_idx])
        
        # Update current position
        scatter_current._offsets3d = ([x[i]], [y[i]], [z[i]])
        
        # Update title
        state_str = "Mobile" if states[i] else "Adsorbed"
        title.set_text(f'{type_names[particle_type]} Particle - Frame {i}/{len(x)}\n'
                      f'State: {state_str}, Cumulative Time: {z[i]:.4f}')
        
        return line, scatter_mobile, scatter_adsorbed, scatter_current, title
    
    num_animation_frames = len(x) // 2  # Since we're showing every 2nd frame
    anim = FuncAnimation(fig, update, init_func=init, 
                        frames=num_animation_frames, 
                        interval=1000//fps, blit=False)
    
    if output_path:
        print(f"Saving animation to: {output_path}")
        print("This may take a few minutes...")
        writer = PillowWriter(fps=fps)
        anim.save(output_path, writer=writer)
        print(f"Animation saved!")
    else:
        plt.show()
    
    plt.close()


def create_levy_khintchine_visualization(trajectory, output_path=None):
    """
    Create visualization showing the Lévy-Khintchine representation.
    
    This shows how the trajectory relates to the mathematical description:
    φ(θ) = exp(t[∫(e^(iθτ) - 1)Π(dτ)])
    
    Components visualized:
    1. Empirical Lévy measure Π(dτ) = λF(dτ) from observed jumps
    2. Characteristic function φ(θ) in complex plane
    3. Jump size distribution F(τ)
    4. Cumulative Lévy measure and its relation to k'
    """
    positions = trajectory['positions']
    states = trajectory['states']
    cum_time = trajectory['cumulative_adsorbed_time']
    particle_type = trajectory['particle_type']
    
    type_names = ['Large (green)', 'Medium (blue)', 'Small (red)']
    
    # Extract ACTUAL adsorption durations (not frame-by-frame increments!)
    # Need to find state transitions: mobile→adsorbed (start) and adsorbed→mobile (end)
    jump_sizes = []
    current_adsorption_start = None
    
    for i in range(len(states)):
        is_mobile = states[i]
        
        # Transition: mobile → adsorbed (start of adsorption event)
        if i > 0 and states[i-1] and not is_mobile:
            current_adsorption_start = i
        
        # Transition: adsorbed → mobile (end of adsorption event)
        if i > 0 and not states[i-1] and is_mobile:
            if current_adsorption_start is not None:
                # Compute duration of this adsorption event
                duration = cum_time[i-1] - cum_time[current_adsorption_start-1]
                if duration > 0:
                    jump_sizes.append(duration)
                current_adsorption_start = None
    
    # Handle case where particle is still adsorbed at the end
    if current_adsorption_start is not None and current_adsorption_start < len(cum_time):
        duration = cum_time[-1] - cum_time[current_adsorption_start-1]
        if duration > 0:
            jump_sizes.append(duration)
    
    jump_sizes = np.array(jump_sizes)
    
    if len(jump_sizes) == 0:
        print("No adsorption events detected. Cannot create Lévy-Khintchine visualization.")
        return
    
    # Calculate total observation time (in real time, not frames)
    frame_indices = np.arange(len(cum_time))
    total_frames = len(cum_time)
    
    # Estimate jump rate λ (jumps per frame)
    lambda_rate = len(jump_sizes) / total_frames
    
    print(f"\nJump size statistics:")
    print(f"  Number of jumps: {len(jump_sizes)}")
    print(f"  Min jump size: {np.min(jump_sizes):.6f}")
    print(f"  Max jump size: {np.max(jump_sizes):.6f}")
    print(f"  Mean jump size: {np.mean(jump_sizes):.6f}")
    print(f"  Std jump size: {np.std(jump_sizes):.6f}")
    print(f"  Unique values: {len(np.unique(jump_sizes))}")
    
    # Create histogram for jump size distribution F(τ)
    # Adaptive binning based on data characteristics
    n_unique = len(np.unique(jump_sizes))
    n_bins = min(20, max(5, n_unique))  # Between 5 and 20 bins, or number of unique values
    
    # Handle case where all jumps are identical or nearly identical
    jump_range = np.max(jump_sizes) - np.min(jump_sizes)
    if jump_range < 1e-10:
        # All jumps are essentially the same size - create a single bin
        bin_centers = np.array([np.mean(jump_sizes)])
        bin_widths = np.array([max(0.001, np.mean(jump_sizes) * 0.1)])  # 10% of mean or minimum
        F_tau = np.array([1.0])  # All probability in one bin
        bin_edges = np.array([bin_centers[0] - bin_widths[0]/2, bin_centers[0] + bin_widths[0]/2])
        print(f"  All jumps nearly identical: τ ≈ {bin_centers[0]:.6f}")
    else:
        hist_counts, bin_edges = np.histogram(jump_sizes, bins=n_bins, density=False)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        bin_widths = np.diff(bin_edges)
        # Normalize to get probability distribution F(τ)
        F_tau = hist_counts / np.sum(hist_counts)
        print(f"  Using {n_bins} bins")
        print(f"  Bin width: {bin_widths[0]:.6f}")
        print(f"  Max probability in a bin: {np.max(F_tau):.6f}")
    
    # Lévy measure: M(dτ) = λ * F(dτ)
    levy_measure = lambda_rate * F_tau / bin_widths  # Per unit τ
    
    # Compute characteristic function φ(θ) for various θ values
    theta_values = np.linspace(-5, 5, 100)
    phi_real = np.zeros_like(theta_values)
    phi_imag = np.zeros_like(theta_values)
    
    for idx, theta in enumerate(theta_values):
        # φ(θ) = exp(t * Σ[e^(iθτ) - 1] * λF(τ))
        exponent = 0
        for i, tau in enumerate(bin_centers):
            weight = F_tau[i] * lambda_rate * total_frames
            exponent += (np.exp(1j * theta * tau) - 1) * weight
        
        phi = np.exp(exponent)
        phi_real[idx] = phi.real
        phi_imag[idx] = phi.imag
    
    # Extract jump arrival times (frames where jumps occur)
    jump_frames = []
    for i in range(1, len(states)):
        # Transition: adsorbed → mobile (end of adsorption event = jump occurrence)
        if not states[i-1] and states[i]:
            jump_frames.append(i)
    
    jump_frames = np.array(jump_frames)
    
    # Compute inter-arrival times (time BETWEEN jumps, not jump sizes!)
    if len(jump_frames) > 1:
        inter_arrival_times = np.diff(jump_frames)  # In frame units
    else:
        inter_arrival_times = np.array([])
    
    print(f"\nPoisson process statistics:")
    print(f"  Number of jump arrivals: {len(jump_frames)}")
    if len(inter_arrival_times) > 0:
        print(f"  Mean inter-arrival time: {np.mean(inter_arrival_times):.2f} frames")
        print(f"  Std inter-arrival time: {np.std(inter_arrival_times):.2f} frames")
        print(f"  Expected mean (1/λ): {1/lambda_rate:.2f} frames")
    
    # Create comprehensive figure with 4 rows (added Poisson panels)
    fig = plt.figure(figsize=(16, 16))
    gs = fig.add_gridspec(4, 3, hspace=0.5, wspace=0.4)
    
    # ROW 0: JUMP SIZES (Exponential component)
    # 1. Jump size distribution F(τ)
    ax1 = fig.add_subplot(gs[0, 0])
    
    # Plot empirical bars - use absolute positioning to ensure visibility
    bars = ax1.bar(bin_centers, F_tau, width=bin_widths*0.8, 
                   alpha=0.7, color='steelblue', edgecolor='black', 
                   linewidth=1.5, label='Empirical')
    
    print(f"\nPlotting histogram:")
    print(f"  Bin centers: {bin_centers[:5]}... (showing first 5)")
    print(f"  F_tau values: {F_tau[:5]}... (showing first 5)")
    print(f"  Bar widths: {bin_widths[:5]}... (showing first 5)")
    
    # Overlay exponential fit for comparison (as points at bin centers)
    tau_mean = np.mean(jump_sizes)
    # Expected probability in each bin for exponential distribution
    # P(bin) = integral from left to right of (1/τ̄)e^(-τ/τ̄) dτ
    expected_probs = []
    for i in range(len(bin_edges) - 1):
        left = bin_edges[i]
        right = bin_edges[i + 1]
        # CDF of exponential: F(x) = 1 - e^(-x/τ̄)
        prob = (np.exp(-left/tau_mean) - np.exp(-right/tau_mean))
        expected_probs.append(prob)
    expected_probs = np.array(expected_probs)
    
    ax1.plot(bin_centers, expected_probs, 'ro-', linewidth=2, markersize=8,
             alpha=0.8, label=f'Exponential (τ̄={tau_mean:.4f})', zorder=10)
    
    ax1.set_xlabel('Jump Size τ (Adsorption Duration)', fontsize=10)
    ax1.set_ylabel('Probability F(τ)', fontsize=10)
    ax1.set_title('Jump Size Distribution F(τ)', fontsize=11, fontweight='bold')
    ax1.legend(fontsize=9, loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(left=0)  # Jump sizes must be non-negative
    
    # Compute KS test statistic for exponential fit
    from scipy import stats as sp_stats
    ks_stat, ks_pval = sp_stats.kstest(jump_sizes, lambda x: 1 - np.exp(-x/tau_mean))
    
    ax1.text(0.05, 0.95, 
             f'n_jumps = {len(jump_sizes)}\n'
             f'τ ∈ [{np.min(jump_sizes):.4f}, {np.max(jump_sizes):.4f}]\n'
             f'τ̄ = {tau_mean:.4f}\n'
             f'KS test: p={ks_pval:.3f}', 
             transform=ax1.transAxes, va='top', fontsize=9,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # 2. Lévy measure Π(dτ) = λF(dτ)
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.bar(bin_centers, levy_measure * bin_widths, width=bin_widths*0.8,
            alpha=0.7, color='darkred', edgecolor='black')
    ax2.set_xlabel('Jump Size τ', fontsize=10)
    ax2.set_ylabel('Π(dτ) = λF(dτ)', fontsize=10)
    ax2.set_title('Lévy Measure Π(dτ)\n(Jump Intensity)', fontsize=11, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(left=0)  # Jump sizes must be non-negative
    ax2.text(0.05, 0.95, 
             f'λ = {lambda_rate:.4f} jumps/frame\n'
             '(Same λ as Poisson rate in Row 1!)', 
             transform=ax2.transAxes, va='top', fontsize=9,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # 3. Cumulative Lévy measure and k' relation
    ax3 = fig.add_subplot(gs[0, 2])
    cumulative_measure = np.cumsum(levy_measure * bin_widths)
    ax3.plot(bin_centers, cumulative_measure, 'o-', color='darkgreen', linewidth=2)
    ax3.set_xlabel('Jump Size τ', fontsize=10)
    ax3.set_ylabel('∫₀^τ Π(dx)', fontsize=10)
    ax3.set_title('Cumulative Lévy Measure\n∫₀^τ Π(dx) ≈ λF(≤τ)', fontsize=11, fontweight='bold')
    ax3.set_xlim(left=0)  # Jump sizes must be non-negative
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=lambda_rate, color='red', linestyle='--', linewidth=1.5, 
                label=f'Total intensity λ={lambda_rate:.4f}')
    ax3.legend(fontsize=8)
    
    # ROW 1: JUMP ARRIVALS (Poisson component)
    # 4. Poisson distribution P(N(T)=k) - THE FUNDAMENTAL DISTRIBUTION
    ax4 = fig.add_subplot(gs[1, 0])
    
    # The single observation from our trajectory
    observed_count = len(jump_sizes)
    expected_count_total = lambda_rate * total_frames
    
    # Plot theoretical Poisson PMF for N(T) ~ Poisson(λT)
    # Show reasonable range around the mean
    k_max = max(int(expected_count_total + 4*np.sqrt(expected_count_total)), observed_count + 5)
    k_values = np.arange(0, k_max + 1)
    poisson_pmf = [sp_stats.poisson.pmf(k, expected_count_total) for k in k_values]
    
    # Bar chart of theoretical distribution
    ax4.bar(k_values, poisson_pmf, width=0.8, alpha=0.6, color='cornflowerblue',
            edgecolor='black', linewidth=1.5, label=f'Poisson(λT={expected_count_total:.1f})')
    
    # Mark where our single observation falls
    if 0 <= observed_count <= k_max:
        obs_prob = sp_stats.poisson.pmf(observed_count, expected_count_total)
        ax4.bar([observed_count], [obs_prob], width=0.8, alpha=0.9, color='red',
                edgecolor='darkred', linewidth=2, label=f'Our trajectory: N={observed_count}')
    
    ax4.set_xlabel('Number of Jumps k', fontsize=10)
    ax4.set_ylabel('Probability P(N=k)', fontsize=10)
    ax4.set_title('Poisson Distribution\nP(N(T)=k | λ, T)', fontsize=11, fontweight='bold')
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.set_xlim(left=-0.5)
    
    # Add explanation
    ax4.text(0.95, 0.95,
             f'Single trajectory:\n'
             f'N(T={total_frames}) = {observed_count}\n'
             f'Expected: λT = {expected_count_total:.1f}\n\n'
             f'This is THE fundamental\n'
             f'Poisson distribution!',
             transform=ax4.transAxes, ha='right', va='top', fontsize=8,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
    
    # 5. Cumulative jump count N(t)
    ax5 = fig.add_subplot(gs[1, 1])
    # Count number of jumps up to each frame
    jump_count = np.zeros(total_frames)
    for jf in jump_frames:
        if jf < total_frames:
            jump_count[jf:] += 1
    
    ax5.plot(frame_indices, jump_count, 'b-', linewidth=2, alpha=0.7, label='N(t)')
    
    # Overlay expected linear growth with slope λ
    expected_count = lambda_rate * frame_indices
    ax5.plot(frame_indices, expected_count, 'r--', linewidth=2, 
             label=f'Expected: λt (λ={lambda_rate:.4f})')
    
    # Scatter actual jump locations
    if len(jump_frames) > 0:
        counts_at_jumps = jump_count[jump_frames]
        ax5.scatter(jump_frames, counts_at_jumps, c='red', s=30, 
                   alpha=0.8, zorder=5)
    
    ax5.set_xlabel('Frame (Time t)', fontsize=10)
    ax5.set_ylabel('Cumulative Jump Count N(t)', fontsize=10)
    ax5.set_title('Counting Process N(t)\n(Linear growth → Poisson)', fontsize=11, fontweight='bold')
    ax5.legend(fontsize=9)
    ax5.grid(True, alpha=0.3)
    
    # 6. Jump count distribution in fixed windows
    ax6 = fig.add_subplot(gs[1, 2])
    if len(jump_frames) > 5:  # Need enough jumps to make windows
        # Divide trajectory into fixed windows and count jumps per window
        window_size = max(10, total_frames // 20)  # ~20 windows
        n_windows = total_frames // window_size
        
        jump_counts_per_window = []
        for w in range(n_windows):
            start_frame = w * window_size
            end_frame = min((w + 1) * window_size, total_frames)
            count = np.sum((jump_frames >= start_frame) & (jump_frames < end_frame))
            jump_counts_per_window.append(count)
        
        jump_counts_per_window = np.array(jump_counts_per_window)
        
        # Histogram of counts
        max_count = max(jump_counts_per_window.max(), 1)
        bins_count = np.arange(0, max_count + 2) - 0.5
        hist_counts, _ = np.histogram(jump_counts_per_window, bins=bins_count)
        
        # Normalize
        prob_counts = hist_counts / np.sum(hist_counts)
        
        x_vals = np.arange(0, max_count + 1)
        ax6.bar(x_vals, prob_counts, width=0.8, alpha=0.7, color='orange',
                edgecolor='black', linewidth=1.5, label='Empirical')
        
        # Overlay Poisson(λ * window_size) distribution
        lambda_window = lambda_rate * window_size
        poisson_probs = [sp_stats.poisson.pmf(k, lambda_window) 
                        for k in range(max_count + 1)]
        ax6.plot(x_vals, poisson_probs, 'ro-', linewidth=2, markersize=8,
                 alpha=0.8, label=f'Poisson(λΔt={lambda_window:.2f})', zorder=10)
        
        ax6.set_xlabel('Number of Jumps per Window', fontsize=10)
        ax6.set_ylabel('Probability', fontsize=10)
        ax6.set_title(f'Jump Count Distribution\n({n_windows} windows, Δt={window_size} frames)', 
                     fontsize=11, fontweight='bold')
        ax6.legend(fontsize=9)
        ax6.grid(True, alpha=0.3)
        ax6.set_xlim(left=-0.5)
        
        ax6.text(0.05, 0.95,
                 f'Window size: {window_size} frames\n'
                 f'Mean count: {np.mean(jump_counts_per_window):.2f}\n'
                 f'Expected: {lambda_window:.2f}',
                 transform=ax6.transAxes, va='top', fontsize=9,
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    else:
        ax6.text(0.5, 0.5, 'Not enough jumps\nfor windowed analysis',
                ha='center', va='center', fontsize=12, transform=ax6.transAxes)
        ax6.set_title('Jump Count Distribution', fontsize=11, fontweight='bold')
    
    # ROW 2: CHARACTERISTIC FUNCTION (Mathematical characterization)
    # 7. Characteristic function - Real part
    ax7 = fig.add_subplot(gs[2, 0])
    ax7.plot(theta_values, phi_real, 'b-', linewidth=2)
    ax7.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
    ax7.axvline(x=0, color='k', linestyle='-', linewidth=0.5)
    ax7.set_xlabel('θ (Frequency)', fontsize=10)
    ax7.set_ylabel('Re[φ(θ)]', fontsize=10)
    ax7.set_title('Characteristic Function - Real Part\nRe[φ(θ)]', fontsize=11, fontweight='bold')
    ax7.grid(True, alpha=0.3)
    
    # Add connection to Poisson components
    ax7.text(0.95, 0.05, 
             'CF encodes BOTH:\n'
             f'• Poisson rate λ={lambda_rate:.4f}\n'
             f'• Exponential F(τ) with τ̄={tau_mean:.4f}\n\n'
             'φ(θ) = exp(t∫[e^(iθτ)-1]λF(dτ))\n'
             '(SAME λ in all rows!)',
             transform=ax7.transAxes, ha='right', va='bottom', fontsize=8,
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
    
    # 8. Characteristic function - Imaginary part
    ax8 = fig.add_subplot(gs[2, 1])
    ax8.plot(theta_values, phi_imag, 'r-', linewidth=2)
    ax8.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
    ax8.axvline(x=0, color='k', linestyle='-', linewidth=0.5)
    ax8.set_xlabel('θ (Frequency)', fontsize=10)
    ax8.set_ylabel('Im[φ(θ)]', fontsize=10)
    ax8.set_title('Characteristic Function - Imaginary Part\nIm[φ(θ)]', fontsize=11, fontweight='bold')
    ax8.grid(True, alpha=0.3)
    
    # Add explanation of oscillation
    ax8.text(0.95, 0.05,
             'Oscillations encode:\n'
             f'• Jump rate λ (amplitude)\n'
             f'• Mean size τ̄ (frequency)\n\n'
             'Faster oscillation →\nlarger typical jumps',
             transform=ax8.transAxes, ha='right', va='bottom', fontsize=8,
             bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.7))
    
    # 9. Characteristic function in complex plane
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.plot(phi_real, phi_imag, 'g-', linewidth=2, alpha=0.7)
    ax9.plot([phi_real[len(phi_real)//2]], [phi_imag[len(phi_imag)//2]], 
             'ro', markersize=10, label='θ=0 (should be 1+0i)')
    ax9.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
    ax9.axvline(x=0, color='k', linestyle='-', linewidth=0.5)
    ax9.set_xlabel('Re[φ(θ)]', fontsize=10)
    ax9.set_ylabel('Im[φ(θ)]', fontsize=10)
    ax9.set_title('Characteristic Function\nComplex Plane Trajectory', fontsize=11, fontweight='bold')
    ax9.grid(True, alpha=0.3)
    ax9.legend(fontsize=8)
    ax9.set_aspect('equal')
    
    # Add interpretation
    ax9.text(0.05, 0.05,
             'Spiral trajectory:\n'
             f'• Decay rate ∝ λt ({len(jump_sizes)} jumps)\n'
             f'• Rotation speed ∝ τ̄ ({tau_mean:.4f})\n\n'
             'Complete CPP signature!',
             transform=ax9.transAxes, ha='left', va='bottom', fontsize=8,
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))
    
    # ROW 3: TRAJECTORY (The resulting CPP)
    # 10. Trajectory staircase (bottom row, full width)
    ax10 = fig.add_subplot(gs[3, :])
    # Show only first 100 frames for clarity
    n_show = min(100, len(cum_time))
    frames_show = frame_indices[:n_show]
    time_show = cum_time[:n_show]
    
    ax10.plot(frames_show, time_show, 'k-', linewidth=1.5, label='t_S(t) trajectory')
    
    # Highlight jumps
    jump_frames_show = np.where(np.diff(time_show) > 0)[0]
    if len(jump_frames_show) > 0:
        ax10.scatter(frames_show[jump_frames_show], time_show[jump_frames_show], 
                   c='red', s=50, alpha=0.8, zorder=5,
                   label=f'{len(jump_frames_show)} jumps shown')
        
        # Draw vertical lines for jumps
        for jf in jump_frames_show[:10]:  # Show first 10 jump annotations
            jump_size = time_show[jf+1] - time_show[jf]
            ax10.annotate('', xy=(frames_show[jf], time_show[jf+1]),
                        xytext=(frames_show[jf], time_show[jf]),
                        arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
            ax10.text(frames_show[jf]+1, (time_show[jf+1]+time_show[jf])/2,
                    f'τ={jump_size:.3f}', fontsize=7, color='red')
    
    ax10.set_xlabel('Frame (Time t)', fontsize=11)
    ax10.set_ylabel('Cumulative Adsorbed Time t_S(t)', fontsize=11)
    ax10.set_title('Compound Poisson Process: t_S(t) = Σᵢ τᵢ (First 100 frames)\n'
                  'Jump SIZES τᵢ ~ F(τ), Jump TIMES ~ Poisson(λ)', 
                  fontsize=11, fontweight='bold')
    ax10.legend(loc='upper left', fontsize=9)
    ax10.grid(True, alpha=0.3)
    
    # Overall title with Lévy-Khintchine formula
    fig.suptitle(
        f'{type_names[particle_type]} Particle - Lévy-Khintchine Representation\n'
        r'$\varphi_X(\theta)(t) = \mathbb{E}[e^{i\theta X(t)}] = \exp\left(t\int_{\mathbb{R}\setminus\{0\}}(e^{i\theta x} - 1)\Pi(dx)\right)$',
        fontsize=14, fontweight='bold', y=0.995
    )
    
    # Add text box with key statistics (updated with Poisson info)
    stats_text = (
        f'Compound Poisson Process Statistics:\n'
        f'JUMP SIZES (Exponential):\n'
        f'• Mean τ̄ = {np.mean(jump_sizes):.4f}\n'
        f'• Std σ_τ = {np.std(jump_sizes):.4f}\n'
        f'JUMP ARRIVALS (Poisson):\n'
        f'• Rate λ = {lambda_rate:.4f} jumps/frame\n'
        f'• Mean inter-arrival = {1/lambda_rate:.2f} frames\n'
        f'OVERALL:\n'
        f'• Total frames: {total_frames}\n'
        f'• Total jumps: {len(jump_sizes)}\n'
        f'• Final t_S: {cum_time[-1]:.4f}'
    )
    
    fig.text(0.02, 0.02, stats_text, fontsize=9,
             verticalalignment='bottom',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nLévy-Khintchine visualization saved to: {output_path}")
    
    plt.show()


def create_projection_views(trajectory, output_path=None):
    """
    Create 2D projection views of the 3D trajectory.
    
    Shows XY (column view), XZ (side view), and YZ (front view) projections.
    """
    positions = trajectory['positions']
    states = trajectory['states']
    cum_time = trajectory['cumulative_adsorbed_time']
    particle_type = trajectory['particle_type']
    
    type_names = ['Large (green)', 'Medium (blue)', 'Small (red)']
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    # Remap coordinates
    x = positions[:, 0]      # Horizontal
    y_sim = positions[:, 1]  # Vertical (simulation Y)
    time = cum_time          # Cumulative time
    
    # XY projection (column top view) - unchanged
    ax1 = axes[0, 0]
    ax1.plot(x, y_sim, 'k-', linewidth=0.5, alpha=0.5)
    ax1.scatter(x[~states], y_sim[~states], c='red', s=3, alpha=0.6, label='Adsorbed')
    ax1.scatter(x[states], y_sim[states], c='blue', s=3, alpha=0.4, label='Mobile')
    ax1.scatter([x[0]], [y_sim[0]], c='lime', s=100, marker='o', edgecolors='black', linewidths=2, label='Start')
    ax1.scatter([x[-1]], [y_sim[-1]], c='orange', s=100, marker='s', edgecolors='black', linewidths=2, label='End')
    ax1.set_xlabel('X Position')
    ax1.set_ylabel('Y Position (Vertical)')
    ax1.set_title('XY Projection (Column Top View)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect('equal')
    xmin, xmax = ax1.get_xlim()
    ax1.set_xlim(max(0, xmin - 0.1), min(1, xmax + 0.1))
    
    # Time vs X (shows horizontal wandering as time progresses)
    ax2 = axes[0, 1]
    ax2.plot(time, x, 'k-', linewidth=1, alpha=0.7)
    ax2.scatter(time[~states], x[~states], c='red', s=3, alpha=0.7, label='Adsorbed')
    ax2.scatter(time[states], x[states], c='blue', s=3, alpha=0.5, label='Mobile')
    ax2.set_xlabel('Cumulative Adsorbed Time (Lévy Process)')
    ax2.set_ylabel('X Position')
    ax2.set_title('Time vs X Position - Horizontal Wandering')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Time vs Y (critical view - shows falling + Lévy process!)
    ax3 = axes[1, 0]
    ax3.plot(time, y_sim, 'k-', linewidth=1, alpha=0.7)
    ax3.scatter(time[~states], y_sim[~states], c='red', s=3, alpha=0.7, label='Adsorbed')
    ax3.scatter(time[states], y_sim[states], c='blue', s=3, alpha=0.5, label='Mobile')
    ax3.set_xlabel('Cumulative Adsorbed Time (Lévy Process)')
    ax3.set_ylabel('Y Position (Vertical)')
    ax3.set_title('Time vs Y - Particle Falls While Time Accumulates!')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Time series of cumulative adsorbed time
    ax4 = axes[1, 1]
    frame_numbers = np.arange(len(time))
    ax4.plot(frame_numbers, time, 'k-', linewidth=1.5)
    
    # Highlight jumps (adsorption events)
    jumps = np.diff(time) > 0
    jump_frames = frame_numbers[1:][jumps]
    jump_values = time[1:][jumps]
    if len(jump_frames) > 0:
        ax4.scatter(jump_frames, jump_values, c='red', s=20, alpha=0.7, 
                   label=f'{len(jump_frames)} adsorption events', zorder=10)
    
    ax4.set_xlabel('Frame Number (Time)')
    ax4.set_ylabel('Cumulative Adsorbed Time')
    ax4.set_title('Lévy Process: t_S(t) vs Time\n(Staircase = Compound Poisson Process)')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    fig.suptitle(f'{type_names[particle_type]} Particle Trajectory - All Views', 
                fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nProjection views saved to: {output_path}")
    
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description='Visualize single particle trajectory as a Lévy process'
    )
    parser.add_argument('--particle', type=int, default=None,
                       help='Particle ID to track (0-indexed). If not specified, picks a representative particle.')
    parser.add_argument('--type', choices=['large', 'medium', 'small'], default=None,
                       help='Particle type to track (if --particle not specified)')
    parser.add_argument('--frames', type=int, default=400,
                       help='Number of frames to simulate (default: 400)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed (default: 42)')
    parser.add_argument('--animate', action='store_true',
                       help='Create animated 3D trajectory (slower)')
    parser.add_argument('--fps', type=int, default=20,
                       help='Frames per second for animation (default: 20)')
    parser.add_argument('--no-interactive', action='store_true',
                       help='Do not show interactive plots')
    
    args = parser.parse_args()
    
    # Determine particle ID
    if args.particle is not None:
        particle_id = args.particle
    else:
        # Pick a representative particle based on type
        # Particles 0-499: large, 500-999: medium, 1000-1499: small
        type_map = {'large': 250, 'medium': 750, 'small': 1250}
        particle_id = type_map.get(args.type, 1250)  # Default to small
        print(f"No particle ID specified, using representative {args.type or 'small'} particle: {particle_id}")
    
    # Run simulation with trajectory tracking
    trajectory = run_with_trajectory_tracking(
        particle_id=particle_id,
        num_frames=args.frames,
        seed=args.seed
    )
    
    # Create visualizations
    print("\n" + "="*70)
    print("CREATING VISUALIZATIONS")
    print("="*70)
    
    # Static 3D plot
    output_3d = molass_path / 'study' / f'levy_trajectory_3d_particle{particle_id}.png'
    create_3d_trajectory_plot(trajectory, output_path=output_3d, 
                             interactive=not args.no_interactive)
    
    # Projection views
    output_proj = molass_path / 'study' / f'levy_trajectory_projections_particle{particle_id}.png'
    create_projection_views(trajectory, output_path=output_proj)
    
    # Lévy-Khintchine representation visualization
    output_lk = molass_path / 'study' / f'levy_khintchine_representation_particle{particle_id}.png'
    create_levy_khintchine_visualization(trajectory, output_path=output_lk)
    
    # Animated trajectory (optional)
    if args.animate:
        output_anim = molass_path / 'study' / f'levy_trajectory_3d_particle{particle_id}_animated.gif'
        create_animated_trajectory(trajectory, output_path=output_anim, fps=args.fps)
    else:
        print("\nTo create animated 3D trajectory, run with --animate flag")
        print("  (Warning: This can take several minutes)")
    
    print("\n" + "="*70)
    print("VISUALIZATION COMPLETE")
    print("="*70)
    print("\nKey Insights:")
    print("- The 3D trajectory shows the Compound Poisson Process structure")
    print("- Horizontal segments: Particle is mobile (free diffusion)")
    print("- Vertical jumps: Particle is adsorbed (random delays accumulate)")
    print("- This is a concrete example of a Lévy process!")
    print("\nLévy-Khintchine Representation Components:")
    print("- F(τ): Jump size distribution from observed adsorptions")
    print("- Π(dτ) = λF(dτ): Lévy measure (jump intensity)")
    print("- φ(θ): Characteristic function in Fourier domain")
    print("- The formula connects microscopic jumps to macroscopic distribution")
    print("\nUse these visualizations to explain:")
    print("1. How physical adsorption creates mathematical 'jumps'")
    print("2. Why SEC separates by size (different jump statistics)")
    print("3. How CPP emerges from microscopic random events")
    print("4. How Lévy-Khintchine triplet (0, 0, Π) characterizes the process")


if __name__ == "__main__":
    main()
