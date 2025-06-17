"""
    FlowChange.FlowChangeJudge.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import numpy as np
from molass.FlowChange.FlowChangeInfo import FlowChangeJudgeInfo

NEAR_SIGMA = 0.3
LIMIT_SIGMA = 1.5           # < 3 for OA_Ald, < 1.8 for 20161217, < 1.52 for 20170309\Backsub
MIN_REL_LIKE = 0.05         # < 0.0732 for 20170301
VERYBAD_ABS_LIKE = 0.0003   # > 0.0002 for 20191109
BAD_ABS_LIKE = 0.00045      # > 0.00033 for 20160227, < 0.000466 for 20190524_1, > 0.00041 for 20190524_2
MIN_ABS_LIKE = 0.003        # > 0.00246 for 20180602, < 0.0048 for ph&
SAFE_REL_LIKE = 0.55        # > 0.525 for 20160227, < 0.574 for 20161216, < 0.646 for pH6
ALLOW_REL_LIKE = 0.25        # < 0.358 for AhRR, > 0.103 for 20170307, < 0.452 for Kosugi8, < 0.29 for 20170304
ALLOW_ABS_LIKE = 0.005      # < 0.00737 for 20170301
SAFE_ABS_LIKE = 0.01
MIN_LIKE = 0.001
Y1_RATIO_LIMIT = 0.1        # < 0.157 for 20180225, > 0.074 for 20160628
Y1_RATIO_SAFE_LIMIT = 0.9
ERR_RATIO_LIMIT = 1.0

class FlowChangeJudge:
    def __init__(self):
        self.init_params = np.array([NEAR_SIGMA, LIMIT_SIGMA, MIN_REL_LIKE, VERYBAD_ABS_LIKE, BAD_ABS_LIKE,
                                     MIN_ABS_LIKE, SAFE_REL_LIKE, ALLOW_REL_LIKE, ALLOW_ABS_LIKE, SAFE_ABS_LIKE,
                                     MIN_LIKE, Y1_RATIO_LIMIT, ERR_RATIO_LIMIT])

    def update_params(self, params_dict):
        for name, value in params_dict.items():
            var = globals().get(name)
            assert var is not None
            var = value

    def restore_params(self):
        pass

    def judge(self, curve1, curve2, mi, points, segments, abs_likes, rel_likes, peaklike, peakpos, debug=False):
        x = curve1.x
        y1 = curve1.y
        y2 = curve2.y
        max_y1 = np.max(y1)
        M, std = mi.get_meanstd()
        N_lb = M - NEAR_SIGMA*std
        N_ub = M + NEAR_SIGMA*std
        M_lb = M - LIMIT_SIGMA*std
        M_ub = M + LIMIT_SIGMA*std
        slope_ratio = abs(y2[0] - y2[-1])/np.std(y2)

        info = None

        if peaklike:
            P_lb = peakpos - LIMIT_SIGMA*std
            P_ub = peakpos + LIMIT_SIGMA*std
        else:
            P_lb = M - LIMIT_SIGMA*std
            P_ub = M + LIMIT_SIGMA*std

        if debug:
            print("slope_ratio=", slope_ratio)
            print("points=", points)
            print("rel_likes=", rel_likes)
        near_count = 0
        inner_count = 0
        for k, p in enumerate(points):
            if N_lb < x[p] and x[p] < N_ub:
                near_count += 1
            if P_lb < x[p] and x[p] < P_ub:
                inner_count += 1

        if debug:
            print("peaklike", peaklike, "inner_count=", inner_count)
        if near_count == 2:
            # as in 20160227
            i, j = None, None
        elif peaklike and inner_count == 2:
            # as in 20190309_1
            i, j = None, None
        else:
            from .Differential import islike_differential
            is_differential = islike_differential(curve1, curve2, debug=debug)
            fc_points = []
            gap0 = segments[1].y[0] - segments[0].y[-1]
            gap1 = segments[2].y[0] - segments[1].y[-1]
            i, j = points
            err_ratio = np.std(y2[i:j])/abs(gap1)
            if debug:
                print("err_ratio=", err_ratio)
            for k, p in enumerate(points):
                abs_like = abs_likes[k]
                rel_like = rel_likes[k]
                y1_ratio = y1[p]/max_y1
                if debug and k == 1:
                    print("y1_ratio=", y1_ratio, "abs_like=", abs_like, "rel_like=", rel_like)
                
                if debug:
                    print(f"point {k}: M_lb={M_lb}, x={x[p]}, M_ub={M_ub}, peaklike={peaklike}")
                if k == 0 and peaklike and M_ub < x[p]:                         # as in 20220716\OA_ALD_202
                    p = None
                elif k == 0 and M_lb < x[p] and is_differential:                # as in 20210323_1, but not in 20171203 (not differential)
                    p = None
                elif (rel_like < MIN_REL_LIKE
                    or abs_like < VERYBAD_ABS_LIKE                              # as in 20191109
                    or peaklike and abs_like < BAD_ABS_LIKE                     # as in 20160227
                    or peaklike and k == 1 and M_lb < x[p] and abs_like < ALLOW_ABS_LIKE  # as in 20180316
                    or peaklike and k == 1 and err_ratio > ERR_RATIO_LIMIT      # as in 20180617
                    or k == 0 and y1_ratio > Y1_RATIO_LIMIT and gap0 > 0        # as in 20180225 (require k == 0 to avoid pH6, gap0 > 0 to avoid 20170309)
                    or k == 0 and M < x[p] and abs_like < ALLOW_ABS_LIKE        # as in 20190630_2
                    or k == 1 and y1_ratio > Y1_RATIO_SAFE_LIMIT and rel_like < SAFE_REL_LIKE   # as in 20180602
                    or k == 1 and M_lb < x[p] and rel_like < ALLOW_REL_LIKE     # as in 20170307
                    or k == 1 and M < x[p] and abs_like < SAFE_ABS_LIKE         # as in Sugiyama  # 
                    or k == 1 and peaklike and x[p] < M_lb and abs_like < MIN_ABS_LIKE  # as in 20190524_2
                    or k == 1 and abs_like < MIN_ABS_LIKE and i is None and rel_like < SAFE_REL_LIKE      # as in 20180602
                    ):
                    p = None
 
                fc_points.append(p)

            if debug:
                print("abs_likes=", abs_likes)
                print("fc_points=", fc_points)

            i, j = fc_points
            if j is not None:
                if (x[j] < M
                    and (rel_likes[1] > SAFE_REL_LIKE       # as in 20161216
                        or rel_likes[1] > ALLOW_REL_LIKE    # as in 20170304
                        or abs_likes[1] > ALLOW_ABS_LIKE    # as in 20170301
                        )
                    ):
                    # as in pH6
                    info = FlowChangeJudgeInfo('pH6', i=i, j=j)
                    i = j
                    j = None

            if i is None and j is not None:
                # as in 20180225
                j = None

        return i, j, info