"""
    Baseline.FlowChangeLikely.py
"""
import numpy as np

NUM_NEIGHBOURS = 10
STD_WIDTH = 30

def compute_yscale(x, y):
    """Compute the y-scale for likelihood computation.

    Parameters
    ----------
    x : array-like
        The x-values of the curve.
    y : array-like
        The y-values of the curve.

    Returns
    -------
    float
        The y-scale value.
    """
    xspan = x[-1] - x[0]
    yspan = np.max(y) - np.min(y)
    return yspan/xspan

def get_safeslice(lb, ub, start, stop):
    """Get a safe slice within the bounds [lb, ub).

    Parameters
    ----------
    lb : int
        The lower bound (inclusive).
    ub : int
        The upper bound (exclusive).
    start : int
        The start index of the slice.
    stop : int
        The stop index of the slice.

    Returns
    -------
    slice
        The safe slice object.
    """
    return slice(max(lb, start), min(ub, stop))

def find_nearest_point(px, py, i, x, y, yscale):
    """Find the nearest point to (px, py) around index i.

    Parameters
    ----------
    px : float
        The x-coordinate of the point.
    py : float
        The y-coordinate of the point.
    i : int
        The index around which to search.
    x : array-like
        The x-values of the curve.
    y : array-like
        The y-values of the curve.
    yscale : float
        The y-scale for distance computation.

    Returns
    -------
    int
        The index of the nearest point.
    """
    slice_ = get_safeslice(0, len(x), i-NUM_NEIGHBOURS, i+NUM_NEIGHBOURS)
    dist = (x[slice_] - px)**2 + ((y[slice_] - py)/yscale)**2
    return slice_.start + np.argmin(dist)

def compute_flowchange_likelihoods(x, y, points, segments, yscale=None, return_neighbours=False):
    """Compute the flow change likelihoods at the given points.

    Parameters
    ----------
    x : array-like
        The x-values of the curve.
    y : array-like
        The y-values of the curve.
    points : list of int
        The breakpoints of the segments.
    segments : list of Linesegment
        The list of line segments.
    yscale : float, optional
        The y-scale for likelihood computation. If None, it will be computed from the data.
    return_neighbours : bool, optional
        If True, also return the neighbouring point indices for each breakpoint.
        Defaults to False.

    Returns
    -------
    likelihoods : array-like
        The normalized likelihoods for each breakpoint.
    neighbours : list of tuples, optional
        If return_neighbours is True, a list of (j, k) tuples where j
        and k are the indices of the nearest points on either side of each breakpoint.
    """
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
    """Compute the flow change likelihood at the given index.

    Parameters
    ----------
    x : array-like
        The x-values of the curve.
    y : array-like
        The y-values of the curve.
    i : int
        The index of the breakpoint.
    seg1 : Linesegment
        The segment before the breakpoint.
    seg2 : Linesegment
        The segment after the breakpoint.
    yscale : float
        The y-scale for likelihood computation.
    neighbours : list of tuples, optional
        If provided, the function will append the (j, k) indices of the nearest points
        on either side of the breakpoint to this list.
    debug : bool, optional
        If True, print debug information.
    
    Returns
    -------
    float
        The likelihood value for the breakpoint.
    """
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