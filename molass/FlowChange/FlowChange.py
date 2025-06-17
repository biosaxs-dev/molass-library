"""
    FlowChange.FlowChange.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.stats import linregress

SLOPE_RATIO_LIMIT = 3.0     # < 3.01 for 20190607_1

def flowchange_exclude_slice_impl(x, y, mi, yscale, debug=False):
    from molass.Geometric.Linesegment import get_segments
    from molass.Geometric.Peaklike import check_peaklike_segment
    from molass.FlowChange.FlowChangeLikely import compute_flowchange_likelihoods
    from molass.Geometric.LinesegmentUtils import reduce_segments

    num_bkpoints = 4
    points, segments = get_segments(x, y, n_bkps=num_bkpoints)
    ret, sign = check_peaklike_segment(x, y, mi, points, segments)
    if debug:
        print("peaklike ret=", ret is not None, sign)
    peaklike = False
    peakpos = None
    if ret is not None:
        peaklike = True
        points, segments, j, k = ret[0:4]
        peakpos = (x[j] + x[k])/2
    likelihoods = compute_flowchange_likelihoods(x, y, points, segments, yscale=yscale)
    like_recs = []
    for k, like in enumerate(likelihoods):
        like_recs.append((k, like))
    like_recs = sorted(like_recs, key=lambda r: r[1])

    remove_recs = []
    num_removed = len(points) - 2
    for k, like in like_recs[0:num_removed]:
        remove_recs.append((k, like))
    if num_removed > 1:
        remove_recs = sorted(remove_recs, key=lambda r: -r[0])      # in order to remove from the right

    likelihoods = list(likelihoods)
    for k, like in remove_recs[0:num_removed]:
        likelihoods.pop(k)
        points.pop(k)
        reduce_segments(segments, k)

    return points, segments, likelihoods, peaklike, peakpos

def flowchange_exclude_slice(curve1, curve2, debug=False, return_fullinfo=False, counter=None, return_firstinfo=False):
    from molass.Stats.Moment import Moment
    from molass.FlowChange.FlowChangeLikely import compute_yscale, flowchange_likelihood
    from molass.FlowChange.FlowChangeJudge import LIMIT_SIGMA, FlowChangeJudge
    x = curve1.x
    y1 = curve1.y
    y2 = curve2.y
    max_y1 = np.max(y1)
    mi = Moment(x, y1)
    M, std = mi.get_meanstd()
    M_lb = M - LIMIT_SIGMA*std
    M_ub = M + LIMIT_SIGMA*std
    slope_ratio = abs(y2[0] - y2[-1])/np.std(y2)

    corrected = False
    if slope_ratio > SLOPE_RATIO_LIMIT:
        # as in 20190607_1 or 20170304
        slope, intercept = linregress(x, y2)[0:2]
        y2_base = x*slope + intercept
        y2_temp = y2.copy()    
        y2_temp -= y2_base
        corrected = True
    else:
        y2_temp = y2
    yscale = compute_yscale(x, y2_temp)
    points, segments, rel_likes, peaklike, peakpos = flowchange_exclude_slice_impl(x, y2_temp, mi, yscale)
    if corrected:
        from molass.Geometric.LinesegmentUtils import restore_segments
        segments = restore_segments(slope, intercept, segments)

    if return_firstinfo:
        return mi, points, segments, rel_likes, peaklike, peakpos, yscale

    abs_likes = []
    for k, p in enumerate(points):
        abs_like = flowchange_likelihood(x, y2, p, segments[k], segments[k+1], yscale)
        abs_likes.append(abs_like)

    judge = FlowChangeJudge()

    i, j, judge_info = judge.judge(curve1, curve2, mi, points, segments, abs_likes, rel_likes, peaklike, peakpos, debug=debug)

    if debug:
        import matplotlib.pyplot as plt
        print("slope_ratio=", slope_ratio)
        fig, ax = plt.subplots()
        ax.plot(x, y1, label='curve1')
        axt = ax.twinx()
        axt.plot(x, y2, color="C1", alpha=0.5, label='curve2')
        for k in i, j:
            if k is not None:
                ax.axvline(x[k], color='cyan')
        fig.tight_layout()
        plt.show()

    if return_fullinfo:
        return (i, j), judge_info, segments, (M_lb, M_ub), std
    else:
        return (i, j), judge_info