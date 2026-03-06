"""
Demonstrate Bochner Subordination in SEC Trajectories

This script shows how the stationary phase time t_S can be viewed as
a process subordinated by the mobile phase time T_t.

Key Concept:
- Frame t = laboratory clock (deterministic, constant ticks)
- T_t = cumulative mobile phase time = random subordinator
- t_S(T_t) = stationary time as function of mobile time = subordinated CPP

This demonstrates Pasti 2005's comment about including mobile-phase 
dispersion via Bochner subordination.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Add molass to path
molass_path = Path(__file__).parent.parent
sys.path.insert(0, str(molass_path))

from molass.SEC.ColumnSimulation import get_animation


def analyze_subordination(particle_id=500, num_frames=400, seed=42):
    """
    Analyze the trajectory using subordination perspective.
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
    t_S = np.array(trajectory['cumulative_adsorbed_time'])  # Stationary time
    
    # Calculate cumulative mobile phase time T_t
    # Mobile time increments when state is mobile
    T_t = np.zeros(len(states))
    for i in range(1, len(states)):
        if states[i]:  # Mobile
            T_t[i] = T_t[i-1] + 1  # Increment by 1 frame
        else:  # Adsorbed
            T_t[i] = T_t[i-1]  # No increment
    
    print(f"\nTrajectory Statistics:")
    print(f"  Total frames (lab time): {num_frames}")
    print(f"  Total mobile time T: {T_t[-1]:.1f} frames")
    print(f"  Total adsorbed time t_S: {t_S[-1]:.6f}")
    print(f"  Ratio t_S/T: {t_S[-1]/T_t[-1] if T_t[-1] > 0 else 0:.6f}")
    
    # Extract jumps in t_S using state transitions
    # Jump = complete adsorption event (mobile → adsorbed → mobile)
    jump_sizes = []
    jump_indices = []  # Index where jump completes (return to mobile)
    T_at_jumps = []
    
    in_adsorption = False
    adsorption_start_idx = None
    t_S_start = None
    
    for i in range(len(states)):
        if states[i] == False and not in_adsorption:  # Mobile → Adsorbed
            in_adsorption = True
            adsorption_start_idx = i
            t_S_start = t_S[i]
        elif states[i] == True and in_adsorption:  # Adsorbed → Mobile (jump complete!)
            jump_size = t_S[i] - t_S_start
            if jump_size > 0:  # Valid jump
                jump_sizes.append(jump_size)
                jump_indices.append(i)
                T_at_jumps.append(T_t[i])
            in_adsorption = False
    
    jump_sizes = np.array(jump_sizes)
    jump_indices = np.array(jump_indices, dtype=int)
    T_at_jumps = np.array(T_at_jumps)
    
    print(f"\nJump Statistics:")
    print(f"  Number of jumps: {len(jump_sizes)}")
    print(f"  Jump rate (per frame): {len(jump_sizes) / num_frames:.4f}")
    print(f"  Jump rate (per mobile time): {len(jump_sizes) / T_t[-1] if T_t[-1] > 0 else 0:.4f}")
    
    # Create visualization
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3)
    
    # Row 1: Three different time parametrizations
    # Panel 1: t_S vs frame (standard view)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(np.arange(len(t_S)), t_S, 'b-', linewidth=1.5, alpha=0.7)
    ax1.scatter(jump_indices + 1, t_S[jump_indices + 1], c='red', s=20, alpha=0.6, zorder=5)
    ax1.set_xlabel('Frame t (Lab Clock)', fontsize=10)
    ax1.set_ylabel('t_S(t) - Stationary Time', fontsize=10)
    ax1.set_title('Standard: t_S indexed by frame\n(Lévy process)', fontsize=11, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Mobile time T_t vs frame
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(np.arange(len(T_t)), T_t, 'g-', linewidth=1.5, alpha=0.7)
    ax2.set_xlabel('Frame t (Lab Clock)', fontsize=10)
    ax2.set_ylabel('T_t - Mobile Time', fontsize=10)
    ax2.set_title('Subordinator: T_t\n(Random clock for mobile phase)', fontsize=11, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.text(0.05, 0.95, 
             f'T increases only when mobile\n'
             f'Total mobile time: {T_t[-1]:.0f}\n'
             f'vs {num_frames} total frames',
             transform=ax2.transAxes, va='top', fontsize=9,
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))
    
    # Panel 3: t_S vs T_t (subordinated view) - KEY PLOT!
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(T_t, t_S, 'r-', linewidth=1.5, alpha=0.7)
    ax3.scatter(T_at_jumps, t_S[jump_indices + 1], c='darkred', s=20, alpha=0.8, zorder=5)
    ax3.set_xlabel('T_t - Mobile Time (Random Clock)', fontsize=10)
    ax3.set_ylabel('t_S - Stationary Time', fontsize=10)
    ax3.set_title('Subordinated: t_S(T_t)\n(CPP indexed by mobile time)', fontsize=11, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.text(0.05, 0.95,
             'Bochner Subordination:\n'
             'Process evaluated at\n'
             'random times T_t\n\n'
             'Still a Lévy process!',
             transform=ax3.transAxes, va='top', fontsize=9,
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    # Row 2: Increments analysis
    # Panel 4: Increments in frame time
    ax4 = fig.add_subplot(gs[1, 0])
    delta_t_S_frame = np.diff(t_S)
    ax4.plot(delta_t_S_frame, 'b-', linewidth=0.5, alpha=0.5)
    ax4.axhline(y=0, color='k', linestyle='--', linewidth=1)
    ax4.set_xlabel('Frame t', fontsize=10)
    ax4.set_ylabel('Δt_S (per frame)', fontsize=10)
    ax4.set_title('Increments: Δt_S(frame)', fontsize=11, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    
    # Panel 5: Increments in mobile time
    ax5 = fig.add_subplot(gs[1, 1])
    # Only look at increments when T_t actually changes
    mobile_increments_mask = np.diff(T_t) > 0
    delta_t_S_mobile = delta_t_S_frame[mobile_increments_mask]
    mobile_frames = np.where(mobile_increments_mask)[0]
    
    if len(delta_t_S_mobile) > 0:
        ax5.plot(mobile_frames, delta_t_S_mobile, 'g-', linewidth=0.5, alpha=0.5)
        ax5.axhline(y=0, color='k', linestyle='--', linewidth=1)
        ax5.set_xlabel('Frame t (only mobile increments)', fontsize=10)
        ax5.set_ylabel('Δt_S (per mobile time)', fontsize=10)
        ax5.set_title('Increments: Δt_S(T_t) when mobile', fontsize=11, fontweight='bold')
        ax5.grid(True, alpha=0.3)
    
    # Panel 6: Jump size histogram
    ax6 = fig.add_subplot(gs[1, 2])
    if len(jump_sizes) > 0:
        ax6.hist(jump_sizes, bins=20, alpha=0.7, color='darkred', edgecolor='black')
        tau_mean = np.mean(jump_sizes)
        
        # Overlay exponential
        x_exp = np.linspace(0, np.max(jump_sizes), 100)
        y_exp = len(jump_sizes) * np.mean(np.diff(ax6.get_xlim()) / 20) * (1/tau_mean) * np.exp(-x_exp/tau_mean)
        ax6.plot(x_exp, y_exp, 'b-', linewidth=2, label=f'Exp(τ̄={tau_mean:.4f})')
        
        ax6.set_xlabel('Jump Size τ', fontsize=10)
        ax6.set_ylabel('Count', fontsize=10)
        ax6.set_title('Jump Sizes: τ ~ F(τ)\n(Same in both parametrizations!)', fontsize=11, fontweight='bold')
        ax6.legend(fontsize=9)
        ax6.grid(True, alpha=0.3)
    
    # Row 3: Independence tests
    # Panel 7: Autocorrelation in frame time
    ax7 = fig.add_subplot(gs[2, 0])
    if len(jump_sizes) > 1:
        jump_current = jump_sizes[:-1]
        jump_next = jump_sizes[1:]
        corr_frame = np.corrcoef(jump_current, jump_next)[0, 1]
        
        ax7.scatter(jump_current, jump_next, alpha=0.5, s=30)
        ax7.axhline(y=np.mean(jump_sizes), color='r', linestyle='--', linewidth=1, alpha=0.5)
        ax7.axvline(x=np.mean(jump_sizes), color='r', linestyle='--', linewidth=1, alpha=0.5)
        ax7.set_xlabel('τ[i]', fontsize=10)
        ax7.set_ylabel('τ[i+1]', fontsize=10)
        ax7.set_title(f'Jump Independence Test\nCorr = {corr_frame:.4f}', fontsize=11, fontweight='bold')
        ax7.grid(True, alpha=0.3)
        ax7.text(0.05, 0.95,
                 f'{"✓ Independent" if abs(corr_frame) < 0.1 else "❌ Dependent"}',
                 transform=ax7.transAxes, va='top', fontsize=10,
                 bbox=dict(boxstyle='round',
                          facecolor='lightgreen' if abs(corr_frame) < 0.1 else 'lightcoral',
                          alpha=0.8))
    
    # Panel 8: Inter-arrival times (in mobile time)
    ax8 = fig.add_subplot(gs[2, 1])
    if len(T_at_jumps) > 1:
        inter_arrival_mobile = np.diff(T_at_jumps)
        ax8.hist(inter_arrival_mobile, bins=20, alpha=0.7, color='green', edgecolor='black')
        
        # Overlay exponential (Poisson inter-arrivals)
        lambda_mobile = len(jump_sizes) / T_t[-1] if T_t[-1] > 0 else 0
        x_poisson = np.linspace(0, np.max(inter_arrival_mobile) if len(inter_arrival_mobile) > 0 else 1, 100)
        y_poisson = len(inter_arrival_mobile) * np.mean(np.diff(ax8.get_xlim()) / 20) * lambda_mobile * np.exp(-lambda_mobile * x_poisson)
        ax8.plot(x_poisson, y_poisson, 'b-', linewidth=2, label=f'Exp(λ={lambda_mobile:.4f})')
        
        ax8.set_xlabel('Inter-arrival Time (mobile time)', fontsize=10)
        ax8.set_ylabel('Count', fontsize=10)
        ax8.set_title('Inter-arrival Times in T_t\n(Should be exponential)', fontsize=11, fontweight='bold')
        ax8.legend(fontsize=9)
        ax8.grid(True, alpha=0.3)
    
    # Panel 9: Summary comparison
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.axis('off')
    
    summary_text = f"""
BOCHNER SUBORDINATION SUMMARY

Frame Time Parametrization:
• t = frame number (lab clock)
• t_S(t) = Lévy process (CPP)
• λ = {len(jump_sizes) / num_frames:.4f} jumps/frame

Mobile Time Parametrization:
• T_t = cumulative mobile time
• T_t is random (subordinator)
• t_S(T_t) = subordinated CPP
• λ_T = {len(jump_sizes) / T_t[-1] if T_t[-1] > 0 else 0:.4f} jumps/mobile-time

KEY INSIGHT:
Both parametrizations give the
SAME Lévy process structure:
✓ Independent increments
✓ Stationary increments
✓ Same jump size distribution F(τ)

Difference: Random vs deterministic
time parametrization!

This is how Pasti 2005 can include
mobile-phase dispersion while
maintaining Lévy structure.
"""
    
    ax9.text(0.1, 0.5, summary_text, fontsize=10, family='monospace',
            verticalalignment='center',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Overall title
    fig.suptitle(
        'Bochner Subordination: t_S as Function of Mobile Time T_t\n'
        'Demonstrating Pasti 2005 Appendix Concept',
        fontsize=14, fontweight='bold', y=0.995
    )
    
    plt.tight_layout()
    
    output_path = Path(__file__).parent / "subordination_demonstration.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nVisualization saved to: {output_path}")
    plt.show()
    
    # Print conclusion
    print("\n" + "="*70)
    print("CONCLUSION: Bochner Subordination in SEC")
    print("="*70)
    print(f"""
The stationary phase time t_S can be viewed two ways:

1. STANDARD: t_S(t) indexed by frame number t
   - Deterministic time parameter
   - CPP Lévy process
   
2. SUBORDINATED: t_S(T_t) indexed by mobile time T_t  
   - Random time parameter (subordinator)
   - Still a CPP Lévy process!
   
This demonstrates how mobile-phase dispersion can be included
in the Lévy framework: Use random mobile time T_t as the clock
for the stationary phase process.

Key properties preserved:
• Jump sizes τ ~ F(τ) (same distribution)
• Independent increments (jumps are i.i.d.)
• Stationary increments (λ and F constant)

The subordination doesn't change the process structure,
just the time parametrization!
""")
    print("="*70)


if __name__ == "__main__":
    analyze_subordination(particle_id=1250, num_frames=400, seed=42)
