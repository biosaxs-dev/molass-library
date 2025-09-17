"""
    PlotUtils.TrimmingPlot.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Rectangle

def ij_from_slice(slice_):
    if slice_ is None:
        i, j = 0, -1
    else:
        start = slice_.start
        i = 0 if start is None else start
        stop = slice_.stop
        j = -1 if stop is None else stop
    return i, j

def plot_trimming_impl(ssd, trim, **kwargs):
    if type(trim) is dict:
        from molass.Trimming.TrimmingInfo import TrimmingInfo
        trim = TrimmingInfo(**trim)

    debug = kwargs.get('debug', False)

    fig = plt.figure(figsize=(16,8))
    gs = GridSpec(2,10)

    title = kwargs.get('title', None)
    if title is not None:
        fig.suptitle(title)

    for i, name in enumerate(["UV", "XR"]):
        ax = fig.add_subplot(gs[i,0])
        ax.set_axis_off()
        ax.text(0.8, 0.5, name, va="center", ha="center", fontsize=20)

    axes = []
    for i in range(2):
        axis_row = []
        for j in range(3):
            start = 1+3*j
            ax = fig.add_subplot(gs[i,start:start+3])
            axis_row.append(ax)
        axes.append(axis_row)
    axes = np.array(axes)
    axes[1,2].set_yscale('log')

    uv_shape = None if ssd.uv is None else ssd.uv.M.shape
    xr_shape = None if ssd.xr is None else ssd.xr.M.shape
    shapes = uv_shape, xr_shape
    uv_iv = None if ssd.uv is None else ssd.uv.iv
    xr_iv = None if ssd.xr is None else ssd.xr.iv
    ivectors = uv_iv, xr_iv
    uv_jv = None if ssd.uv is None else ssd.uv.jv
    xr_jv = None if ssd.xr is None else ssd.xr.jv
    jvectors = uv_jv, xr_jv
    ret_info = trim.uv_slices, trim.xr_slices
    vnames = "w", "q"

    # Rectangles
    n = 0
    for ax, shape, iv, jv, info_list, vname in zip(axes[:,0], shapes, ivectors, jvectors, ret_info, vnames):
        if n == 0:
            ax.set_title("Trimmed Range Rectangle")
        n += 1
        if shape is None:
            continue

        ax.invert_yaxis()
        a_info, e_info = info_list
        # print("info_list=", info_list)
        j_max = shape[1] - 1
        i_max = shape[0] - 1
        e_min = jv[0]
        e_max = jv[j_max]
        ax.plot([e_min, e_max, e_max, e_min, e_min],
                [0, 0, i_max, i_max, 0])

        j_stt = 0 if e_info is None else 0 if e_info.start is None else e_info.start
        e_stt = jv[j_stt]
        j_end = j_max if e_info is None else j_max if e_info.stop is None else e_info.stop - 1
        e_end = jv[j_end]
        i_stt = 0 if a_info is None else 0 if a_info.start is None else a_info.start
        a_stt = iv[i_stt]
        i_end = i_max if a_info is None else i_max if a_info.stop is None else a_info.stop - 1
        a_end = iv[i_end]

        range_width = e_end - e_stt
        range_height = i_end - i_stt
        rect = Rectangle(
                (e_stt, i_stt), # (x,y)
                range_width,    # width
                range_height,   # height
                facecolor   = 'green',
                alpha       = 0.1,
            )
        ax.add_patch(rect)

        entire_width = j_max
        entire_height = i_max
        is_narrow = range_width/entire_width < 0.7

        ty = (i_stt + i_end)/2
        for k, j in enumerate([j_stt, j_end]):
            dx = entire_width * (0.5 - k) * 0.2
            if is_narrow:
                dy = entire_height * (0.5 - k) * 0.2
            else:
                dy = 0
            ax.annotate("%d" % jv[j], xy=(jv[j], ty+dy), xytext=(jv[j]+dx, ty+dy), ha="center", va="center", arrowprops=dict(arrowstyle="->", color='k'))

        tx = (e_stt + e_end)/2
        for k, i in enumerate([i_stt, i_end]):
            dy = entire_height * (0.5 - k) * 0.25
            ax.annotate("%s[%d]=%.3g" % (vname, i, iv[i]), xy=(tx, i), xytext=(tx, i+dy), ha="center", va="center", arrowprops=dict(arrowstyle="->", color='k'))

        ax.text(tx, ty, "entire shape=%s" % str(shape), ha="center", va="center")

        axt = ax.twinx()
        axt.invert_yaxis()
        axt.grid(False)
        axt.plot([e_min, e_max, e_max, e_min, e_min],
                iv[[0, 0, i_max, i_max, 0]], alpha=0)

    baseline = kwargs.get('baseline', False)
    uv_baseline = None
    xr_baseline = None

    # Elution curves
    if ssd.uv is None:
        uv_icurve = None
        uv_islice = None
        uv_k = None
    else:
        uv_icurve = ssd.uv.get_icurve()
        uv_islice = trim.uv_slices[1]
        if baseline:
            uv_baseline = ssd.uv.get_ibaseline(debug=True)
        uv_k = np.argmax(uv_icurve.y)

    if ssd.xr is None:
        xr_icurve = None
        xr_islice = None
        xr_k = None
    else:
        xr_icurve = ssd.xr.get_icurve()
        xr_islice = trim.xr_slices[1]
        if baseline:
            xr_baseline = ssd.xr.get_ibaseline(debug=True)
        xr_k = np.argmax(xr_icurve.y)
        if trim.mapping is not None and uv_icurve is not None:
            uv_k = trim.mapping.get_mapped_index(xr_k, xr_icurve.x, uv_icurve.x)
 
    colors = "C0", "orange"
    n = 0
    for ax, icurve, islice, _baseline, k, color in zip(axes[:,1],
                                  (uv_icurve, xr_icurve),
                                  (uv_islice, xr_islice),
                                  (uv_baseline, xr_baseline),
                                  (uv_k, xr_k),
                                  colors,
                                  ):
        if n == 0:
            ax.set_title("Elution Range")
        n += 1
        if icurve is None:
            continue
        ax.plot(icurve.x, icurve.y, color=color, alpha=0.5)
        i, j = ij_from_slice(islice)
        ax.axvspan(*icurve.x[[i,j]], color='green', alpha=0.1)
        ax.axvline(icurve.x[k], color='yellow')
        if _baseline is not None:
            ax.plot(_baseline.x, _baseline.y, color='red')

    # Spectral Curves
    if ssd.uv is None:
        uv_jcurve = None
        uv_jslice = None
        uv_pick = None
    else:
        uv_jcurve = ssd.uv.get_jcurve(uv_k)
        uv_jslice = trim.uv_slices[0]
        uv_pick = ssd.uv.get_ipickvalues()[0]
    if ssd.xr is None:
        xr_jcurve = None
        xr_jslice = None
        xr_pick = None
    else:
        xr_jcurve = ssd.xr.get_jcurve(xr_k)
        xr_jslice = trim.xr_slices[0]
        xr_pick = ssd.xr.get_ipickvalue()

    n = 0
    for ax, jcurve, jslice, pick, color in zip(axes[:,2],
                                  (uv_jcurve, xr_jcurve),
                                  (uv_jslice, xr_jslice),
                                  (uv_pick, xr_pick),
                                  colors,
                                  ):
        if n == 0:
            ax.set_title("Spectral Range")
        n += 1
        if jcurve is None:
            continue
        ax.plot(jcurve.x, jcurve.y, color=color, alpha=0.5)
        i, j = ij_from_slice(jslice)
        ax.axvspan(*jcurve.x[[i,j]], color='green', alpha=0.1)
        ax.axvline(pick, color='yellow')

    fig.tight_layout()
    fig.subplots_adjust(wspace=1.2)
    if debug:
        plt.show()

    from molass.PlotUtils.PlotResult import PlotResult
    return PlotResult(fig, axes, trimming=trim)