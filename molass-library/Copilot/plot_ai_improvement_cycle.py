"""
plot_ai_improvement_cycle.py

Visualises the AI-friendliness improvement feedback loop (Rule 11 in
molass-library/Copilot/copilot-guidelines.md) as a circular flow diagram.

Usage:
    python Copilot/plot_ai_improvement_cycle.py
    # → saves ai_improvement_cycle.png next to this script
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

# ── Step definitions ──────────────────────────────────────────────────────
# (label, example_annotation, box_color)
STEPS = [
    (
        "1  AI-assisted\nresearch",
        "e.g. notebook work\nwith real data",
        "#4C9BE8",
    ),
    (
        "2  Friction\ndetected",
        "e.g. RgCurve.y contains None\n→ TypeError in downstream code",
        "#E85C4C",
    ),
    (
        "3  File GitHub\nissue",
        "gh issue create\n--label \"enhancement\"",
        "#F0A030",
    ),
    (
        "4  Implement fix\nin library",
        "float('nan') instead of None\ndtype=float guaranteed",
        "#48B878",
    ),
    (
        "5  Add test\n& verify",
        "pytest: assert y.dtype == float\nassert None not in y",
        "#48B878",
    ),
    (
        "6  Close issue &\nsimplify notebook",
        "gh issue close #22\nrg_y = rgcurve.y  # clean",
        "#A060D0",
    ),
]

# ── Layout ────────────────────────────────────────────────────────────────
n = len(STEPS)
R_node = 2.6          # radius of node circle
R_annot = 4.0         # radius of annotation text circle
BOX_W = 1.15          # half-width of node box
BOX_H = 0.55          # half-height of node box
ARROW_SHRINK = 48     # shrink arrowhead away from box edge (points)

fig, ax = plt.subplots(figsize=(12, 12))
ax.set_aspect('equal')
ax.axis('off')
ax.set_xlim(-5.5, 5.5)
ax.set_ylim(-5.5, 5.5)

# Angles: start at top, go clockwise
angles = [np.pi / 2 - 2 * np.pi * i / n for i in range(n)]
node_xy = np.array([(R_node * np.cos(a), R_node * np.sin(a)) for a in angles])
annot_xy = np.array([(R_annot * np.cos(a), R_annot * np.sin(a)) for a in angles])

# ── Draw arrows between consecutive nodes ─────────────────────────────────
for i in range(n):
    x0, y0 = node_xy[i]
    x1, y1 = node_xy[(i + 1) % n]
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle="-|>",
            color="#888888",
            lw=2.2,
            mutation_scale=22,
            connectionstyle="arc3,rad=0.18",
            shrinkA=ARROW_SHRINK,
            shrinkB=ARROW_SHRINK,
        ),
    )

# ── Draw node boxes ───────────────────────────────────────────────────────
for i, ((x, y), (label, example, color)) in enumerate(zip(node_xy, STEPS)):
    ax.text(
        x, y, label,
        ha='center', va='center',
        fontsize=12, fontweight='bold', color='white',
        bbox=dict(
            boxstyle='round,pad=0.5',
            facecolor=color,
            edgecolor='white',
            linewidth=2.5,
            alpha=0.92,
        ),
        zorder=5,
    )

# ── Draw annotation text (examples) ──────────────────────────────────────
for i, ((x, y), (label, example, color)) in enumerate(zip(annot_xy, STEPS)):
    ax.text(
        x, y, example,
        ha='center', va='center',
        fontsize=9, color='#333333',
        style='italic',
        bbox=dict(
            boxstyle='round,pad=0.35',
            facecolor='#F8F8F8',
            edgecolor=color,
            linewidth=1.5,
            alpha=0.88,
        ),
    )
    # Connector line from node to annotation
    nx, ny = node_xy[i]
    ax.plot([nx, x], [ny, y], color=color, lw=0.8, ls='dotted', alpha=0.6, zorder=1)

# ── Central label ─────────────────────────────────────────────────────────
ax.text(
    0, 0,
    "AI-friendliness\nimprovement\ncycle\n(molass-library Rule 11)",
    ha='center', va='center',
    fontsize=13, color='#222222',
    style='italic',
    bbox=dict(
        boxstyle='round,pad=0.6',
        facecolor='#F0F0F0',
        edgecolor='#AAAAAA',
        linewidth=1.5,
    ),
)

# ── Title ─────────────────────────────────────────────────────────────────
ax.set_title(
    "molass-library: AI-Friendliness Improvement Feedback Loop",
    fontsize=15, fontweight='bold', pad=14,
)

# ── Legend for colors ─────────────────────────────────────────────────────
legend_patches = [
    mpatches.Patch(color="#4C9BE8", label="Research phase"),
    mpatches.Patch(color="#E85C4C", label="Problem discovery"),
    mpatches.Patch(color="#F0A030", label="Issue tracking"),
    mpatches.Patch(color="#48B878", label="Fix & test"),
    mpatches.Patch(color="#A060D0", label="Closure & cleanup"),
]
ax.legend(
    handles=legend_patches,
    loc='lower center',
    bbox_to_anchor=(0.5, -0.04),
    ncol=5,
    fontsize=9,
    framealpha=0.9,
)

plt.tight_layout()

output = "Copilot/ai_improvement_cycle.png"
plt.savefig(output, dpi=150, bbox_inches='tight')
print(f"Saved: {output}")
plt.show()
