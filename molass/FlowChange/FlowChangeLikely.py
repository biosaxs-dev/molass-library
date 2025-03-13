"""
    Baseline.FlowChangeLikely.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np

NUM_NEIGHBOURS = 10
STD_WIDTH = 30

def compute_yscale(x, y):
    xspan = x[-1] - x[0]
    yspan = np.max(y) - np.min(y)
    return yspan/xspan

def get_safeslice(lb, ub, start, stop):
    return slice(max(lb, start), min(ub, stop))

def find_nearest_point(px, py, i, x, y, yscale):
    slice_ = get_safeslice(0, len(x), i-NUM_NEIGHBOURS, i+NUM_NEIGHBOURS)
    dist = (x[slice_] - px)**2 + ((y[slice_] - py)/yscale)**2
    return slice_.start + np.argmin(dist)

def compute_flowchange_likelihoods(x, y, points, segments, yscale=None, return_neighbours=False):
    if yscale is None:
        yscale = compute_yscale(x, y)
    likelihoods = []
    neighbours = [] if return_neighbours else None
    for n, i in enumerate(points):
        like = flowchange_likelihood(x, y, i, segments[n], segments[n+1], yscale, neighbours=neighbours)
        likelihoods.append(like)
    likelihoods = np.array(likelihoods)/np.sum(likelihoods)

    if return_neighbours:
        return likelihoods, neighbours
    else:
        return likelihoods

def flowchange_likelihood(x, y, i, seg1, seg2, yscale, neighbours=None, debug=False):
    px1 = seg1.x[-1]
    py1 = seg1.y[-1]
    j = find_nearest_point(px1, py1, i, x, y, yscale)
    slice_ = get_safeslice(0, len(x), j-STD_WIDTH, j)       # left-size std 
    stdj = np.std(y[slice_])
    px2 = seg2.x[0]
    py2 = seg2.y[0]
    k = find_nearest_point(px2, py2, i, x, y, yscale)
    slice_ = get_safeslice(0, len(x), k, k+STD_WIDTH)       # right-side std
    stdk = np.std(y[slice_])
    if neighbours is not None:
        neighbours.append((j,k))
    gap = abs(py1 - py2)
    ratio = abs(y[k] - y[j])/max(1, abs(x[k] - x[j]))
    if debug:
        print("j,k =", j, k)
        print("gap=", gap, "ratio=", ratio, "stdj=", stdj, "stdk=", stdk)
        if j == k:
            import matplotlib.pyplot as plt
            from molass.Geometric.Linesegment import plot_segments 
            fig, ax = plt.subplots()
            plot_segments(x, y, [seg1, seg2], ax=ax)
            ax.plot(x[j], y[j], 'o', color='red')

    return gap*ratio/min(stdj, stdk)