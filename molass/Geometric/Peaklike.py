"""
    Geometric.Peaklike.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import numpy as np
from molass.Geometric.Linesegment import get_segments, to_negative_segments
GAPRATIO_LIMIT = 0.65       # < 0.764 for OA_Ald_Fer, < 0.721 for 20190309_5
ERRRATIO_LIMIT = 0.00029    # < 0.0005 for OA_Ald_Fer, > 0.00024 for Kosugi8, < 0.00030 for pH6
PEAKLIKE_NSIGMA = 2

def judge_peaklike_segment(x, y, mi, points, segments, entire_height, i, debug=False):
    if i == 0 or i == len(segments) - 1:
        # not peaklike
        return None

    lgap = segments[i].y[0] - np.min(segments[i-1].y[[0,-1]])
    rgap = segments[i].y[-1] - np.min(segments[i+1].y[[0,-1]])
    peak_gap = (lgap + rgap)/2
    gap_ratio = peak_gap/entire_height
    err_ratio = segments[i].std_err/entire_height

    if debug:
        print("i=", i, "gap_ratio=", gap_ratio, "stderr_ratio=", err_ratio)

    if (gap_ratio > GAPRATIO_LIMIT
        and err_ratio > ERRRATIO_LIMIT
        and mi.is_in_nsigma(PEAKLIKE_NSIGMA, segments[i].center_x)
        ):
        k = 3 - i
        if k < i:
            kgap = abs(segments[k].y[0] - segments[k-1].y[-1])
        else:
            kgap = abs(segments[k].y[-1] - segments[k+1].y[0])
        if debug:
            print("lgap, rgap, kgap=", lgap, rgap, kgap)
        ly = segments[i-1].y[-1]
        ry = segments[i+1].y[0]
        # peaklike_slope = segments[i-1].slope > 0 and segments[i+1].slope < 0
        if min(lgap, rgap) > kgap:
            # as in OA_Ald_Ferr
            if debug:
                print("************* it's peak-like!")
            j = points[i-1]
            k = points[i]
            yval = min(ly, ry)
            new_y = np.concatenate([y[:j], np.ones(k-j)*yval, y[k:]])
            points, segments = get_segments(x, new_y, n_bkps=3)
            ret, sign = check_peaklike_segment(x, new_y, mi, points, segments)
            if ret is not None:
                points, segments, j, k, new_y = ret

            return points, segments, j, k, new_y
        else:
            # as in 20160227
            pass

    return None

def check_peaklike_segment(x, y, mt, points, segments, debug=False):
    heights = []
    for n, seg in enumerate(segments):
        heights.append((n, seg.center_y))
    heights = sorted(heights, key=lambda x: -x[1])
    i = heights[0][0]   # index of heighest segment
    j = heights[-1][0]  # index of lowest segment
    entire_height = segments[i].center_y - segments[j].center_y
    if debug:
        print("i, j =", i, j)

    ret = judge_peaklike_segment(x, y, mt, points, segments, entire_height, i, debug=debug)
    if ret is None:
        # try negative case as in 20190524_1
        if debug:
            print("trying the negative case")
        segmengs_ = to_negative_segments(segments)
        ret = judge_peaklike_segment(x, -y, mt, points, segmengs_, entire_height, j, debug=debug)
        if ret is None:
            return ret, 0
        else:
            points, segments, j, k, new_y = ret
            segmengs_ = to_negative_segments(segments)
            return (points, segmengs_, j, k, -new_y), -1
    else:
        return ret, +1