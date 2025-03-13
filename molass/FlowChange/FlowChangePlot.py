"""
    FlowChange.FlowChangePlot.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import os
import numpy as np
import matplotlib.pyplot as plt
from molass.FlowChange.FlowChangeParams import TEST_TARGETS

def make_plot(recs, axes=None):
    if axes is None:
        fig, axes = plt.subplots(ncols=2, figsize=(16,8), subplot_kw=dict(projection='3d'))
    else:
        fig = axes[0].get_figure()
    
    ax1, ax2 = axes
    ax1.set_title("(i,j) Plot")
    ax2.set_title("j only Plot")
    for i, rec in enumerate(recs):
        target = TEST_TARGETS[i]
        in_folder, mi, points, abs_likes, rel_likes, peaklike, peakpos = rec
        xyz_list = []
        test_results = target[1]
        for j, (a, r, p) in enumerate(zip(abs_likes, rel_likes, points)):
            k = 1 if peaklike else 0
            color = 'C%d' % (j*2 + k)
            if a > 0.1:
                print(in_folder, "a=", a)
            else:
                alpha = 0.3 if test_results[j] is None else 1
                if j == 0:
                    print_values = False
                    if in_folder.find('pH6') >= 0:
                        color = 'red'
                        print_values = True
                    elif in_folder.find('20180602') >= 0:
                        color = 'yellow'
                        print_values = True
                    if print_values:
                        print(in_folder, peaklike, abs_likes, rel_likes)
                ax1.plot(a, r, p, 'o', color=color, alpha=alpha)
                xyz_list.append((a, r, p))
                if j == 1:
                    ax2.plot(a, r, p, 'o', color=color, alpha=alpha)

        if len(xyz_list) == 2:
            xyz = np.array(xyz_list)
            ax1.plot(*xyz.T, ":", color='gray', alpha=0.3)

    for ax in axes:
        ax.set_xlabel('Absolute Likelihood')
        ax.set_ylabel('Relative Likelihood')
        ax.set_zlabel('Point Position')

    fig.tight_layout()
    fig.subplots_adjust(top=0.9)
