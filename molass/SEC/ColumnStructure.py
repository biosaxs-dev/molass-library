"""
    Stochastic.ColumnStructure.py

    Copyright (c) 2024-2025, Molass Community
"""
import numpy as np
from matplotlib.patches import Rectangle, Circle
from .ColumnElements import NewGrain, solvant_color

def plot_column_structure(ax, xmin, xmax, ymin, ymax, num_pores, rs):

    xm = 0.01
    ym = 0.03

    circle_cxv = np.linspace(xmin, xmax, 7)
    circle_cyv = np.flip(np.linspace(ymin+ym+rs, ymax-ym-rs, 12))

    ax.set_axis_off()

    p = Rectangle(
                (xmin, ymin),      # (x,y)
                xmax - xmin,          # width
                ymax - ymin,    # height
                facecolor   = solvant_color,
                # alpha       = 0.2,
            )
    ax.add_patch(p)

    def plot_circles(radius, color="gray", alpha=1, create_grains=False, draw_rectangle=False, debug=False):
        if create_grains:
            grains = []
        
        for i, y in enumerate(circle_cyv):
            for j, x in enumerate(circle_cxv):
                if i%2 == 0:
                    if j%2 == 0:
                        continue
                else:
                    if j%2 == 1:
                        continue

                if create_grains:
                    grain = NewGrain((i, j), (x, y), radius, num_pores)

                if draw_rectangle:
                    p = Rectangle((x-radius, y-radius*4.5), radius*2, radius*9, color=color, alpha=alpha)
                else:
                    p = Circle((x, y), radius, color=color, alpha=alpha)
                    if create_grains:
                        grain = NewGrain((i, j), (x, y), radius, num_pores)
                        if debug:
                            print("create_grains: ", (i, j), (x, y))
                            grain.draw_entries(ax)
                        grains.append(grain)
                ax.add_patch(p)

        if create_grains:
            return grains

    grains = plot_circles(rs, create_grains=True)

    for grain in grains:
        grain.draw(ax)

    """
    set_xlim or set_ylim must be called after plot_circles maybe due to NewGrain.graw which calles ax.pie
    """
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)

    return grains