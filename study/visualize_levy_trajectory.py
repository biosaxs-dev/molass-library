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
    print("\nUse these visualizations to explain:")
    print("1. How physical adsorption creates mathematical 'jumps'")
    print("2. Why SEC separates by size (different jump statistics)")
    print("3. How CPP emerges from microscopic random events")


if __name__ == "__main__":
    main()
