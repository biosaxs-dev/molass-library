"""
Calculate and adjust packing fraction for SEC animation to match 3D realism.

The 2D animation uses circles to represent spherical packing particles.
This script calculates the current 2D packing fraction and suggests
adjustments to match realistic 3D sphere packing (~0.64).
"""

import numpy as np

# Current animation parameters
xmin, xmax = 0.35, 0.65
ymin, ymax = 0, 1
rs = 0.04  # grain radius
num_pores = 16

# Column dimensions
column_width = xmax - xmin
column_height = ymax - ymin
column_area = column_width * column_height

print("="*70)
print("CURRENT 2D PACKING ANALYSIS")
print("="*70)
print(f"Column dimensions: {column_width:.3f} × {column_height:.3f} = {column_area:.4f}")
print(f"Grain radius: rs = {rs:.4f}")

# Count grains (from ColumnStructure logic)
circle_cxv = np.linspace(xmin, xmax, 7)
circle_cyv = np.flip(np.linspace(ymin+0.03+rs, ymax-0.03-rs, 12))

num_grains = 0
for i in range(len(circle_cyv)):
    for j in range(len(circle_cxv)):
        if i % 2 == 0:
            if j % 2 == 0:
                continue
        else:
            if j % 2 == 1:
                continue
        num_grains += 1

print(f"Number of grains: {num_grains}")

# Calculate packing fraction
grain_area = np.pi * rs**2
total_grain_area = num_grains * grain_area
packing_fraction_2d = total_grain_area / column_area

print(f"\nGrain area (each): π×{rs:.4f}² = {grain_area:.6f}")
print(f"Total grain area: {num_grains} × {grain_area:.6f} = {total_grain_area:.6f}")
print(f"**Current 2D packing fraction: {packing_fraction_2d:.4f} ({packing_fraction_2d*100:.2f}%)**")

# Target 3D packing fractions
print("\n" + "="*70)
print("TARGET 3D PACKING FRACTIONS")
print("="*70)
print("Random close packing (RCP): ~0.64 (64%)")
print("Face-centered cubic (FCC): ~0.74 (74%)")
print("Body-centered cubic (BCC): ~0.68 (68%)")

target_3d = 0.64  # Use RCP as target

print(f"\n**Using RCP target: {target_3d:.4f} ({target_3d*100:.2f}%)**")

# Option 1: Adjust grain radius
target_total_area = target_3d * column_area
target_grain_area = target_total_area / num_grains
rs_new = np.sqrt(target_grain_area / np.pi)

print("\n" + "="*70)
print("OPTION 1: ADJUST GRAIN RADIUS")
print("="*70)
print(f"Current rs = {rs:.4f}")
print(f"**New rs = {rs_new:.4f}** (reduction: {(1 - rs_new/rs)*100:.1f}%)")
print(f"This makes grains smaller to create more mobile phase volume")

# Option 2: Reduce number of grains
target_num_grains = int(target_3d * column_area / grain_area)

print("\n" + "="*70)
print("OPTION 2: REDUCE NUMBER OF GRAINS")
print("="*70)
print(f"Current num_grains = {num_grains}")
print(f"**New num_grains = {target_num_grains}** (reduction: {num_grains - target_num_grains} grains)")
print(f"This requires modifying the grid layout in ColumnStructure.py")

# Option 3: Increase column width
width_scale = np.sqrt(packing_fraction_2d / target_3d)
xmin_new = 0.5 - (column_width * width_scale) / 2
xmax_new = 0.5 + (column_width * width_scale) / 2

print("\n" + "="*70)
print("OPTION 3: INCREASE COLUMN WIDTH")
print("="*70)
print(f"Current xmin, xmax = {xmin:.2f}, {xmax:.2f} (width = {column_width:.2f})")
print(f"**New xmin, xmax = {xmin_new:.2f}, {xmax_new:.2f}** (width = {xmax_new-xmin_new:.2f})")
print(f"Width increase: {width_scale*100:.1f}%")

# Recommendation
print("\n" + "="*70)
print("RECOMMENDATION")
print("="*70)
print(f"**Option 1 (Adjust radius) is simplest:**")
print(f"   Change rs = {rs:.4f} → {rs_new:.4f}")
print(f"   Single parameter change in ColumnSimulation.py line ~54")
print(f"\nThis will:")
print(f"  • Reduce grain size by {(1 - rs_new/rs)*100:.1f}%")
print(f"  • Increase mobile phase volume")
print(f"  • Make adsorption less frequent (more realistic)")
print(f"  • Better match 3D SEC column behavior")

# Verification
print("\n" + "="*70)
print("VERIFICATION WITH NEW PARAMETERS")
print("="*70)
new_grain_area = np.pi * rs_new**2
new_total_grain_area = num_grains * new_grain_area
new_packing_fraction = new_total_grain_area / column_area
print(f"New grain area (each): π×{rs_new:.4f}² = {new_grain_area:.6f}")
print(f"New total grain area: {num_grains} × {new_grain_area:.6f} = {new_total_grain_area:.6f}")
print(f"**New packing fraction: {new_packing_fraction:.4f} ({new_packing_fraction*100:.2f}%)**")
print(f"Target: {target_3d:.4f} ({target_3d*100:.2f}%)")
print(f"Match: ✓" if abs(new_packing_fraction - target_3d) < 0.001 else f"Error: {abs(new_packing_fraction - target_3d):.4f}")

print("\n" + "="*70)
print("IMPLEMENTATION")
print("="*70)
print("To implement Option 1, edit ColumnSimulation.py:")
print(f"   Line ~54: rs = 0.04")
print(f"   Change to: rs = {rs_new:.4f}")
print("\nOr add a parameter:")
print(f"   rs = {rs_new:.4f}  # Adjusted to match 3D packing fraction ~0.64")
