"""
    Trimming.TrimmingUtils.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import numpy as np
from molass.Global.Options import get_molass_options
from molass.Trimming.TrimmingInfo import TrimmingInfo

TRIMMING_NSIGMAS = 10

def make_and_slicepair(pair1, pair2, judge_info, debug=False):
    if debug:
        print("judge_info=", judge_info)
    i, j = pair1

    if judge_info is None:
        k, l = pair2
    else:
        # as in pH6
        k, l = None, None

    if i is None:
        start = k
    else:
        start = None if k is None else max(i,k)
    if j is None:
        stop = l
    else:
        stop = None if l is None else min(j,l)
    return start, stop

def make_trimming_impl(ssd, xr_qr=None, xr_mt=None, uv_wr=None, uv_mt=None, uv_fc=None, flowchange=None,
                            ip_effect_info=None, nsigmas=TRIMMING_NSIGMAS, nguiniers=None,
                            jranges=None, mapping=None,
                            debug=False):
    if jranges is None:
        # xr_slices
        if ssd.xr is None or ssd.trimmed:
            xr_islice = None
            xr_jslice = None
        else:
            if xr_qr is None:
                start, stop = ssd.xr.get_usable_qrange(ip_effect_info=ip_effect_info, nguiniers=nguiniers)
            else:
                start, stop = xr_qr
            xr_islice = slice(start, stop)

            if xr_mt is None:
                from molass.Stats import EghMoment
                xr_icurve = ssd.xr.get_icurve()
                xr_mt = EghMoment(xr_icurve)
            start, stop = xr_mt.get_nsigma_points(nsigmas)
            xr_jslice = slice(start, stop)

        # uv_slices
        if ssd.uv is None or ssd.trimmed:
            uv_islice = None
            uv_jslice = None
            mapping = ssd.mapping
        else:
            if uv_wr is None:
                start, stop = ssd.uv.get_usable_wrange()
            else:
                start, stop = uv_wr
            uv_islice = slice(start, stop)

            if uv_mt is None:
                from molass.Stats import EghMoment
                uv_icurve = ssd.uv.get_icurve()
                uv_mt = EghMoment(uv_icurve)
            start, stop = uv_mt.get_nsigma_points(nsigmas)

            if flowchange is None:
                flowchange = get_molass_options('flowchange')

            if flowchange == 'auto':
                from molass.FlowChange.Possibility import possibly_has_flowchange_points
                flowchange = possibly_has_flowchange_points(ssd)

            if flowchange:
                (i, j), judge_info = ssd.uv.get_flowchange_points()
                start, stop = make_and_slicepair((start, stop), (i, j), judge_info)

            uv_jslice = slice(start, stop)

            if mapping is None:
                if get_molass_options('mapped_trimming'):
                    xr_jslice, uv_jslice, mapping = make_mapped_trimming_info(ssd, xr_jslice, uv_jslice, debug=debug)
                    ssd.mapping = mapping
    else:
        # jranges is specified
        if len(jranges) != 2 or len(jranges[0]) != 2 or len(jranges[1]) != 2:
            raise ValueError("jranges must be a tuple of (start, end)")

        from bisect import bisect_right
        xr_islice = slice(None, None)
        xr_jslice = slice(bisect_right(ssd.xr.jv, jranges[0][0]),
                          bisect_right(ssd.xr.jv, jranges[0][1]))

        uv_islice = slice(None, None)
        uv_jslice = slice(bisect_right(ssd.uv.jv, jranges[1][0]),
                          bisect_right(ssd.uv.jv, jranges[1][1]))
        
        assert mapping is not None, "Mapping must be provided when jranges is specified"

    if debug:
        print("xr_islice:", xr_islice)
        print("xr_jslice:", xr_jslice)
        print("uv_islice:", uv_islice)
        print("uv_jslice:", uv_jslice)

    return TrimmingInfo(xr_slices=(xr_islice, xr_jslice), uv_slices=(uv_islice, uv_jslice), mapping=mapping)

def slice_to_values(vec, slice_):
    values = []
    for i, j in (slice_.start, 0), (slice_.stop, -1):
        k = j if i is None else i
        values.append(vec[k])
    return values

def make_mapped_trimming_info(ssd, xr_jslice, uv_jslice, debug=False):
    mapping = ssd.estimate_mapping(debug=debug) 

    xr_x = mapping.xr_curve.x
    xr_ends = slice_to_values(xr_x, xr_jslice)

    ainv = 1/mapping.slope
    binv = -mapping.intercept/mapping.slope

    uv_x = mapping.uv_curve.x
    uv_ends = slice_to_values(uv_x, uv_jslice)
    mp_ends = [x*ainv + binv for x in uv_ends]

    trimmed_ends = max(xr_ends[0], mp_ends[0]), min(xr_ends[1], mp_ends[1])
    if debug:
        print("xr_ends:", xr_ends)
        print("mp_ends:", mp_ends)
        print("trimmed_ends:", trimmed_ends)
    xr_indeces = [int(x - xr_x[0]) for x in trimmed_ends]
    uv_indeces = [int(x*mapping.slope + mapping.intercept - uv_x[0]) for x in trimmed_ends]

    return slice(*xr_indeces), slice(*uv_indeces), mapping
    