"""
Simple diagnostic script to check if trajectory tracking works.
Run this and check the output to see what's being collected.
"""

import sys
from pathlib import Path

molass_path = Path(__file__).parent.parent
sys.path.insert(0, str(molass_path))

from molass.SEC.ColumnSimulation import get_animation

print("="*70)
print("TRAJECTORY TRACKING DIAGNOSTIC")
print("="*70)

# Create animation with trajectory tracking
print("\n1. Creating animation with trajectory tracking...")
print("   Tracking particle ID: 1250")
print("   Number of frames: 50 (small test)")

anim, stats = get_animation(
    num_frames=50,
    seed=42,
    close_plot=True,
    track_particle_id=1250,
    use_tqdm=False,  # Disable progress bar for cleaner output
    blit=False
)

print("\n2. Animation created. Now checking stats dictionary...")

# Check what's in stats
print(f"\n   Keys in stats: {list(stats.keys())}")

if 'trajectory' in stats:
    print("\n3. ✓ Trajectory key exists!")
    traj = stats['trajectory']
    print(f"   Trajectory keys: {list(traj.keys())}")
    
    print(f"\n4. Checking trajectory data:")
    print(f"   - Particle ID: {traj.get('particle_id', 'NOT FOUND')}")
    print(f"   - Particle type: {traj.get('particle_type', 'NOT FOUND')}")
    
    positions = traj.get('positions', [])
    states = traj.get('states', [])
    cum_time = traj.get('cumulative_adsorbed_time', [])
    
    print(f"   - Positions array shape: {positions.shape if hasattr(positions, 'shape') else len(positions)}")
    print(f"   - States array shape: {states.shape if hasattr(states, 'shape') else len(states)}")
    print(f"   - Cumulative time array shape: {cum_time.shape if hasattr(cum_time, 'shape') else len(cum_time)}")
    
    if len(positions) == 0:
        print("\n   ✗ ERROR: Arrays are EMPTY!")
        print("   This means frames were not executed.")
        print("\n   DIAGNOSIS: Animation frames need to be rendered for data collection.")
        print("   The trajectory data is collected during animate() calls.")
    else:
        print(f"\n   ✓ SUCCESS: Arrays contain data!")
        print(f"   - First position: {positions[0]}")
        print(f"   - Last position: {positions[-1]}")
        print(f"   - Final cumulative time: {cum_time[-1]:.6f}")
        print(f"   - Particle was mobile: {sum(states)} frames")
        print(f"   - Particle was adsorbed: {sum(~states)} frames")
else:
    print("\n3. ✗ ERROR: No 'trajectory' key in stats!")
    print("   Available keys:", list(stats.keys()))

print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)
print("\nTO FIX IF ARRAYS ARE EMPTY:")
print("The animation frames must be executed. Try one of these:")
print("1. Call anim.save('temp.gif') to force frame execution")
print("2. Manually call: for i in range(50): anim._func(i)")
print("3. Use matplotlib's event loop")
