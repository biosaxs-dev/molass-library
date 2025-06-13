"""
Mapping.Grouping.py
"""
import numpy as np
from scipy.stats import linregress
from sklearn.cluster import KMeans

def get_groupable_peaks(xr_curve, uv_curve, just_return_peaks=False, debug=False):
    """
    Get peaks that can be grouped for mapping.
    This function is a placeholder and should be implemented based on specific criteria for grouping peaks.
    """

    xr_peaks = np.array(xr_curve.get_peaks(debug=debug))
    uv_peaks = np.array(uv_curve.get_peaks(debug=debug))
    if just_return_peaks:
        return xr_peaks, uv_peaks
    num_groups = max(len(xr_peaks), len(uv_peaks))
    if num_groups > 3:
        # as in protein5 where grouping is not applicable
        ret_xr_peaks, ret_uv_peaks = xr_peaks, uv_peaks
    else:
        success, ret_xr_peaks, ret_uv_peaks = get_groupable_peaks_impl(xr_curve, uv_curve, num_groups, xr_peaks, uv_peaks, debug=debug)
        if success and len(xr_peaks) != len(uv_peaks):
            if len(xr_peaks) < num_groups:
                xr_peaks_ = np.array(xr_curve.get_peaks(num_peaks=num_groups))
            else:
                xr_peaks_ = xr_peaks
            if len(uv_peaks) < num_groups:
                uv_peaks_ = np.array(uv_curve.get_peaks(num_peaks=num_groups))
            else:
                uv_peaks_ = uv_peaks
            success, ret_xr_peaks_, ret_uv_peaks_ = get_groupable_peaks_impl(xr_curve, uv_curve, num_groups, xr_peaks_, uv_peaks_, debug=debug)
            if success:
                if debug:
                    print(f"Re-evaluated peaks: xr_peaks={ret_xr_peaks_}, uv_peaks={ret_uv_peaks_}")
                ret_xr_peaks, ret_uv_peaks = ret_xr_peaks_, ret_uv_peaks_
    return ret_xr_peaks, ret_uv_peaks

def get_groupable_peaks_impl(xr_curve, uv_curve, num_groups, xr_peaks, uv_peaks, debug=False):
    """
    Get peaks that can be grouped for mapping.
    This function is a placeholder and should be implemented based on specific criteria for grouping peaks.
    """
    xr_positions = xr_curve.x[xr_peaks]/xr_curve.x[-1]
    uv_positions = uv_curve.x[uv_peaks]/uv_curve.x[-1]
    points = np.concatenate([xr_positions, uv_positions])
    X = points.reshape((len(points), 1))
    kmeans = KMeans(n_clusters=num_groups, random_state=0).fit(X)
    labels = kmeans.labels_

    xr_select = []
    uv_select = []
    for k in range(num_groups):
        indices = np.where(labels == k)[0]
        xr_indices = indices[indices < len(xr_positions)]
        uv_indices = indices[indices >= len(xr_positions)] - len(xr_positions)
        if len(xr_indices) == 0 or len(uv_indices) == 0:
            continue

        if len(xr_indices) == 1 and len(uv_indices) == 1:
            xr_select.append(xr_indices[0])
            uv_select.append(uv_indices[0])
            continue
        
        if len(xr_indices) == 1:
            xr_select.append(xr_indices[0])
        else:
            assert len(xr_indices) > 1, "Unexpected number of XR indices"
            m = np.argmax(xr_curve.y[xr_peaks[xr_indices]])
            xr_select.append(xr_indices[m])

        if len(uv_indices) == 1:
            uv_select.append(uv_indices[0])
        else:
            assert len(uv_indices) > 1, "Unexpected number of UV indices"
            m = np.argmax(uv_curve.y[uv_peaks[uv_indices]])
            uv_select.append(uv_indices[m])

    if debug:
        import matplotlib.pyplot as plt
        print("labels=", labels, "xr_select=", xr_select, "uv_select=", uv_select)
        fig, ax = plt.subplots()
        fig.suptitle("Groupable Peaks")
        ax.set_xlabel("Normalized Position")
        ax.plot(uv_positions, np.ones_like(uv_positions)*0.7, 'o', label='UV Peaks')
        ax.plot(xr_positions, np.ones_like(xr_positions)*0.5, 'o', label='XR Peaks')
        for k, p in enumerate(points):
            q = 0.5 if k < len(xr_positions) else 0.7
            ax.annotate(str(labels[k]), xy=(p, q), xytext=(p, q+0.1),
                        arrowprops=dict(arrowstyle='->', color='gray'))

        ax.text(0.2, 0.3, f"Number of groups: {num_groups}")
        ax.text(0.2, 0.2, f"uv_labels: {labels[len(xr_peaks):]}; xr_labels: {labels[:len(xr_peaks)]}")
        ax.text(0.2, 0.1, f"uv_select: {uv_select}; xr_select: {xr_select} ")

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.legend()
        plt.show()

    if len(xr_select) > 0 and len(xr_select) == len(uv_select):
        # as in OA_ALD_201
        return True, xr_peaks[xr_select], uv_peaks[uv_select]
    else:
        # as in 20160628
        print("Warning: The number of selected peaks does not match between XR and UV curves.")
        return False, xr_peaks, uv_peaks