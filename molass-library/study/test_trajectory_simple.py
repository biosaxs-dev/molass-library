"""
Simple test of trajectory tracking without animation rendering.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path

molass_path = Path(__file__).parent.parent
sys.path.insert(0, str(molass_path))

from molass.SEC.ColumnSimulation import get_animation

print("Running simple trajectory test...")
print("Tracking particle 1250 for 200 frames...")

# Get animation with trajectory tracking
anim, stats = get_animation(
    num_frames=200,
    seed=42,
    close_plot=True,
    track_particle_id=1250,
    use_tqdm=True,
    blit=False
)

print("\nTrajectory data collected!")
trajectory = stats['trajectory']

print(f"Particle type: {trajectory['particle_type']}")  # 2 = small (red)
print(f"Number of frames: {len(trajectory['positions'])}")
print(f"Final cumulative adsorbed time: {trajectory['cumulative_adsorbed_time'][-1]:.6f}")

# Quick 3D plot
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

positions = trajectory['positions']
cum_time = trajectory['cumulative_adsorbed_time']

x = positions[:, 0]
y = positions[:, 1]
z = cum_time

# Plot trajectory
ax.plot(x, y, z, 'k-', linewidth=1, alpha=0.7)
ax.scatter([x[0]], [y[0]], [z[0]], c='lime', s=100, marker='o', label='Start')
ax.scatter([x[-1]], [y[-1]], [z[-1]], c='red', s=100, marker='s', label='End')

ax.set_xlabel('X Position')
ax.set_ylabel('Y Position')
ax.set_zlabel('Cumulative Adsorbed Time (Lévy Process)')
ax.set_title('3D Trajectory - Compound Poisson Process')
ax.legend()

output_path = molass_path / 'study' / 'test_levy_trajectory_3d.png'
plt.savefig(output_path, dpi=150)
print(f"\nPlot saved to: {output_path}")

plt.show()
