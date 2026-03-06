"""
Test whether spatial position Y(t) has independent increments.

For a process to have independent increments, Y(t₂) - Y(t₁) must be 
independent of Y(t₁) - Y(t₀) for non-overlapping time intervals.

We'll test this by checking correlation between consecutive increments.
If they're independent, correlation should be ~0.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Add molass to path
molass_path = Path(__file__).parent.parent
sys.path.insert(0, str(molass_path))

from molass.SEC.ColumnSimulation import get_animation


def test_position_independence(particle_id=500, num_frames=400, seed=42):
    """
    Test whether spatial position increments are independent.
    """
    print(f"Collecting trajectory for particle {particle_id}...")
    print(f"  Frames: {num_frames}")
    print(f"  Seed: {seed}")
    
    # Run simulation with trajectory tracking
    anim, stats = get_animation(
        num_frames=num_frames,
        seed=seed,
        close_plot=True,
        track_particle_id=particle_id,
        use_tqdm=True,
        blit=False
    )
    
    # Execute all frames to collect trajectory data
    print("Executing animation frames to collect trajectory...")
    try:
        for i in range(num_frames):
            anim._func(i)
    except Exception as e:
        print(f"Note: Some frames may have had issues: {e}")
        print("Continuing with collected data...")
    
    # Extract trajectory data
    trajectory = stats['trajectory']
    positions = np.array(trajectory['positions'])
    states = np.array(trajectory['states'])
    
    # Calculate vertical position Y(t) (assuming column is vertical)
    Y_t = positions[:, 1]  # Y-coordinate (vertical)
    
    print(f"\nAnalyzing {len(Y_t)} frames...")
    
    # Calculate increments
    delta_Y = np.diff(Y_t)  # Y(t+1) - Y(t)
    
    # Check for independence by computing correlation between consecutive increments
    # If independent: Corr(ΔY[i], ΔY[i+1]) ≈ 0
    # NOTE: Correlation = 0 is NECESSARY but NOT SUFFICIENT for independence!
    if len(delta_Y) > 1:
        delta_Y_current = delta_Y[:-1]  # ΔY[i]
        delta_Y_next = delta_Y[1:]      # ΔY[i+1]
        
        correlation = np.corrcoef(delta_Y_current, delta_Y_next)[0, 1]
        print(f"\n=== TEST 1: LINEAR INDEPENDENCE (Necessary but not sufficient) ===")
        print(f"Correlation between consecutive increments: {correlation:.6f}")
        print(f"Expected if independent: ~0.0")
        
        if abs(correlation) > 0.1:
            print(f"❌ FAILS: |correlation| = {abs(correlation):.3f} >> 0")
            print(f"   Since Corr(ΔY[t], ΔY[t+1]) ≠ 0, they are NOT independent.")
        else:
            print(f"✓ Passes: correlation ≈ 0")
            print(f"   But this only rules out LINEAR dependence, not all dependence!")
            print(f"   Need further tests...")
    
    # DIRECT TEST OF INDEPENDENCE: Conditional probability
    # For Lévy process: P(ΔY[t+1] ∈ S | ΔY[t] ∈ T) = P(ΔY[t+1] ∈ S)
    # If they're different, increments are NOT independent!
    if len(delta_Y) > 1:
        small_threshold = np.median(np.abs(delta_Y)) * 0.5
        small_increments = np.abs(delta_Y_current) < small_threshold
        
        # Among small increments, how many are followed by small increments?
        if np.sum(small_increments) > 10:  # Need enough samples
            p_small_given_small = np.mean(np.abs(delta_Y_next[small_increments]) < small_threshold)
            p_small_overall = np.mean(np.abs(delta_Y_next) < small_threshold)
            
            print(f"\n=== TEST 2: INDEPENDENT INCREMENTS (Lévy process definition) ===")
            print(f"Testing: P(|ΔY[t+1]| < θ | |ΔY[t]| < θ) ?= P(|ΔY[t+1]| < θ)")
            print(f"")
            print(f"P(|ΔY[t+1]| < threshold | |ΔY[t]| < threshold) = {p_small_given_small:.3f}")
            print(f"P(|ΔY[t+1]| < threshold)                      = {p_small_overall:.3f}")
            print(f"Difference: {abs(p_small_given_small - p_small_overall):.3f}")
            
            if abs(p_small_given_small - p_small_overall) > 0.1:
                print(f"❌ FAILS INDEPENDENCE! Conditional ≠ Marginal probability")
                print(f"   This DIRECTLY violates Lévy process definition:")
                print(f"   Knowing ΔY[t] tells us about ΔY[t+1] → NOT independent increments!")
            else:
                print(f"✓ Conditional ≈ marginal probability → independent increments")
    
    # DIAGNOSTIC: Why does independence fail? (Not part of Lévy definition, but explains mechanism)
    mobile_mask = states[:-1]  # State at time t (start of each increment)
    adsorbed_mask = ~mobile_mask
    
    mean_increment_when_mobile = np.mean(np.abs(delta_Y[mobile_mask]))
    mean_increment_when_adsorbed = np.mean(np.abs(delta_Y[adsorbed_mask]))
    
    print(f"\n=== DIAGNOSTIC: Why independence fails (if it does) ===")
    print(f"(This is NOT testing Lévy definition, just explaining the mechanism)")
    if np.isnan(mean_increment_when_adsorbed):
        print(f"Mean |ΔY| when mobile: {mean_increment_when_mobile:.6f}")
        print(f"Mean |ΔY| when adsorbed: N/A (particle never adsorbed)")
        print(f"Explanation: Particle stayed mobile throughout.")
    else:
        print(f"Mean |ΔY| when mobile:   {mean_increment_when_mobile:.6f}")
        print(f"Mean |ΔY| when adsorbed: {mean_increment_when_adsorbed:.6f}")
        ratio = mean_increment_when_mobile / (mean_increment_when_adsorbed + 1e-10)
        print(f"Ratio: {ratio:.1f}x")
        
        if ratio > 2.0:
            print(f"")
            print(f"Explanation of dependence mechanism:")
            print(f"  1. Hidden state S(t) ∈ {{mobile, adsorbed}} affects motion")
            print(f"  2. If ΔY[t] ≈ 0, particle likely adsorbed at t")
            print(f"  3. State persists → likely still adsorbed at t+1")
            print(f"  4. Therefore ΔY[t+1] likely also ≈ 0")
            print(f"  5. This creates dependence: P(ΔY[t+1]|ΔY[t]) ≠ P(ΔY[t+1])")
        else:
            print(f"State-dependence is weak in this trajectory.")
    
    # Test for stationary increments
    # Split trajectory into chunks and compare distributions
    n_chunks = 4
    chunk_size = len(delta_Y) // n_chunks
    
    print(f"\n=== TEST 3: STATIONARY INCREMENTS (Lévy process definition) ===")
    print(f"Testing: Does ΔY have same distribution throughout time?")
    print(f"Splitting trajectory into {n_chunks} chunks...")
    print(f"")
    
    chunk_means = []
    chunk_stds = []
    for i in range(n_chunks):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < n_chunks - 1 else len(delta_Y)
        chunk = delta_Y[start:end]
        chunk_means.append(np.mean(chunk))
        chunk_stds.append(np.std(chunk))
        print(f"  Chunk {i+1}: mean={chunk_means[-1]:+.6f}, std={chunk_stds[-1]:.6f}")
    
    mean_variation = np.std(chunk_means)
    print(f"")
    print(f"Variation in chunk means: {mean_variation:.6f}")
    print(f"Expected if stationary: ~0 (all chunks should have same mean)")
    
    if mean_variation > np.mean(chunk_stds) / 10:
        print(f"❌ FAILS stationarity! Mean changes significantly across time")
    else:
        print(f"✓ Means similar across chunks → stationary increments")
    
    # Visualization
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Panel 1: Position trajectory
    ax1 = axes[0, 0]
    ax1.plot(Y_t, linewidth=1)
    ax1.set_xlabel('Frame t')
    ax1.set_ylabel('Y(t) - Vertical Position')
    ax1.set_title('Position Trajectory Y(t)\n(NOT a Lévy Process)')
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Increments
    ax2 = axes[0, 1]
    ax2.plot(delta_Y, linewidth=0.5, alpha=0.7)
    ax2.axhline(y=0, color='r', linestyle='--', linewidth=1)
    ax2.set_xlabel('Frame t')
    ax2.set_ylabel('ΔY(t) = Y(t+1) - Y(t)')
    ax2.set_title('Position Increments')
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: Scatter plot of consecutive increments
    ax3 = axes[1, 0]
    if len(delta_Y) > 1:
        ax3.scatter(delta_Y_current, delta_Y_next, alpha=0.5, s=10)
        ax3.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)
        ax3.axvline(x=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)
        ax3.set_xlabel('ΔY[t]')
        ax3.set_ylabel('ΔY[t+1]')
        ax3.set_title(f'Independence Test\nCorrelation = {correlation:.3f}\n(Should be ~0 if independent)')
        ax3.grid(True, alpha=0.3)
        
        # Add correlation info
        ax3.text(0.05, 0.95, 
                 f'Correlation: {correlation:.4f}\n'
                 f'{"❌ NOT independent" if abs(correlation) > 0.1 else "✓ Independent"}',
                 transform=ax3.transAxes, va='top', fontsize=9,
                 bbox=dict(boxstyle='round', 
                          facecolor='lightcoral' if abs(correlation) > 0.1 else 'lightgreen', 
                          alpha=0.7))
    
    # Panel 4: Increment distribution by state
    ax4 = axes[1, 1]
    if np.any(mobile_mask):
        ax4.hist(delta_Y[mobile_mask], bins=30, alpha=0.5, label='Mobile', color='blue', density=True)
    if np.any(adsorbed_mask):
        ax4.hist(delta_Y[adsorbed_mask], bins=30, alpha=0.5, label='Adsorbed', color='red', density=True)
    ax4.set_xlabel('ΔY')
    ax4.set_ylabel('Density')
    ax4.set_title('Increment Distribution by State\n(State-dependence → NOT independent increments)')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Add note if no adsorbed states
    if not np.any(adsorbed_mask):
        ax4.text(0.5, 0.5, 'Note: Particle never adsorbed\nin this trajectory!',
                ha='center', va='center', fontsize=10, transform=ax4.transAxes,
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    
    plt.tight_layout()
    
    output_path = Path(__file__).parent / "position_independence_test.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nVisualization saved to: {output_path}")
    plt.show()
    
    # FINAL VERDICT
    print("\n" + "="*70)
    print("SUMMARY: Is Y(t) a Lévy process?")
    print("="*70)
    
    # Check test results
    fails_correlation = abs(correlation) > 0.1 if len(delta_Y) > 1 else False
    
    if len(delta_Y) > 1 and np.sum(np.abs(delta_Y_current) < np.median(np.abs(delta_Y)) * 0.5) > 10:
        small_threshold = np.median(np.abs(delta_Y)) * 0.5
        small_increments = np.abs(delta_Y_current) < small_threshold
        p_small_given_small = np.mean(np.abs(delta_Y_next[small_increments]) < small_threshold)
        p_small_overall = np.mean(np.abs(delta_Y_next) < small_threshold)
        fails_independence = abs(p_small_given_small - p_small_overall) > 0.1
    else:
        fails_independence = False
    
    fails_stationarity = mean_variation > np.mean(chunk_stds) / 10
    
    print(f"")
    print(f"Lévy Process Requirements:")
    print(f"  1. Independent increments:  {'❌ FAIL' if (fails_correlation or fails_independence) else '✓ PASS'}")
    print(f"  2. Stationary increments:   {'❌ FAIL' if fails_stationarity else '✓ PASS'}")
    print(f"")
    
    if fails_correlation or fails_independence:
        print(f"CONCLUSION: Y(t) is NOT a Lévy process")
        print(f"")
        print(f"Why? The TEST 2 result shows:")
        print(f"  P(ΔY[t+1] ∈ S | ΔY[t] ∈ T) ≠ P(ΔY[t+1] ∈ S)")
        print(f"")
        print(f"This directly violates the independence requirement.")
        print(f"Future increments depend on past increments through")
        print(f"the hidden state (mobile vs. adsorbed).")
    else:
        print(f"Y(t) appears to satisfy Lévy properties in THIS trajectory.")
        print(f"")
        print(f"Note: This may be trajectory-specific (e.g., particle never")
        print(f"adsorbed). Try different particle_id to see typical behavior.")
    
    print(f"")
    print(f"In contrast, t_S(t) = cumulative adsorbed time IS a Lévy process:")
    print(f"  ✓ Independent increments (Poisson arrivals + i.i.d. jump sizes)")
    print(f"  ✓ Stationary increments (constant λ and F(τ) throughout)")
    print("="*70)


if __name__ == "__main__":
    test_position_independence(particle_id=1250)
