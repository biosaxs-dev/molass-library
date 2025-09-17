"""
    DataUtils.AnomalyHandlers.py
"""
import numpy as np
from scipy.signal import find_peaks

BUBBLE_WIDTH_RANGE = (1, 5)
BUBBLE_SEARCH_WIDTH = 10
BUBBLE_GRADIENT_LIMIT = 0.03

def bubble_check_impl(y, debug=False):
    """
    Check for bubbles in the intensity array.
    
    Parameters
    ----------
    y : np.ndarray
        The intensity array to be checked for bubbles.       
    debug : bool
        If True, debug information will be printed.

    Returns
    -------
    bubbles : np.ndarray
        The indices of the detected bubbles.
    """
    max_y = np.max(y)
    height = max_y*0.9
    width = BUBBLE_WIDTH_RANGE
    prominence = height
    peaks, _ = find_peaks(y, height=height, width=width, prominence=prominence)
    if len(peaks) > 0:
        assert len(peaks) == 1
        m = peaks[0]
        start = max(0, m - BUBBLE_SEARCH_WIDTH)
        stop = min(m + BUBBLE_SEARCH_WIDTH, len(y))
        y_ = y[start:stop]
        gy = np.abs(np.gradient(y_))/max_y
        bubbles = start + np.where(gy > BUBBLE_GRADIENT_LIMIT)[0]
    else:
        bubbles = np.array([], dtype=int)
    if debug:
        import matplotlib.pyplot as plt
        x = np.arange(len(y))
        fig, ax = plt.subplots()
        ax.set_title("find_peaks(y, height=%.3g, width=%s, prominence=%.3g)" % (height, width, prominence))
        ax.plot(x, y)
        ax.plot(x[bubbles], y[bubbles], 'o', color='orange', alpha=0.5)
        ax.plot(x[peaks], y[peaks], 'o', color='red', alpha=0.5)
        axt = ax.twinx()
        if False:
            x_ = x[start:stop]
            axt.plot(x_, gy, 'x')
    return bubbles

def remove_bubbles_impl(intensity_array, to_be_excluded, excluded_set, debug=False):
    """
    Exclude bubbles from the intensity array.

    Parameters
    ----------
    intensity_array : np.ndarray
        The intensity array to be modified.
    to_be_excluded : np.ndarray
        The indices of the bubbles to be excluded.
    excluded_set : set
        The set of excluded indices.
    debug : bool
        If True, debug information will be printed.

    Returns
    -------
    excluded_set : set
        The set of excluded indices.

    """
    from_ = None
    for i in to_be_excluded:
        if from_ is None:
            from_ = i
        else:
            if i > last + 1:
                exclude_bubble_impl(intensity_array, from_, last, excluded_set)
                from_ = i

        last = i
    if from_ is not None:
        exclude_bubble_impl(intensity_array, from_, last, excluded_set)

    return excluded_set

def exclude_bubble_impl(intensity_array, from_, to_, excluded_set):
    """
    Exclude a bubble from the intensity array.
    """
    print( 'exclude_bubble_impl: ', from_, to_ )
    size = intensity_array.shape[0]
    if from_ == 0:
        j = to_ + 1
        for i in range( from_, j ):
            intensity_array[i, :, 1:] = intensity_array[j, :, 1:]
            excluded_set.add(i)
    elif to_ == size - 1:
        j = from_ - 1
        for i in range( from_, size ):
            intensity_array[i, :, 1:] = intensity_array[j, :, 1:]
            excluded_set.add(i)
    else:
        lower = from_ - 1
        upper = to_ + 1
        lower_intensity = intensity_array[lower, :, : ]
        upper_intensity = intensity_array[upper, :, : ]
        width = upper - lower
        for i in range( 1, width ):
            w = i/width
            intensity = ( 1 - w  ) * lower_intensity[ :, 1: ] + w * upper_intensity[ :, 1: ]
            intensity_array[lower+i, :, 1:] = intensity
            excluded_set.add(lower+i)