"""
Peaks.RecognizerSpecific.py
"""

def bridge_recognize_peaks(x, y, num_peaks=None, debug=False):
    """
    Bridge function to recognize peaks in a curve using the legacy method.
    This function is a wrapper around the legacy peak recognition method
    when `num_peaks` is specified.
    Parameters
    ----------
    x : array-like
        The x-coordinates of the curve.
    y : array-like
        The y-coordinates of the curve.
    num_peaks : int, optional
        The number of peaks to recognize. If None, the legacy method will not be used.
    debug : bool, optional
        If True, additional debugging information will be printed and plotted.

    Returns
    -------
    list
        A list of indices where peaks are found in the curve.
    """
    from molass_legacy.QuickAnalysis.ModeledPeaks import recognize_peaks
    params_list = recognize_peaks(x, y, num_peaks=num_peaks, exact_num_peaks=num_peaks, debug=debug)
    peaks = []
    for h, m, s, t in params_list:
        peaks.append(int(round(m - x[0])))
    if debug:
        import matplotlib.pyplot as plt
        plt.plot(x, y, label='Curve')
        plt.scatter(x[peaks], y[peaks], color='red', label='Peaks')
        plt.legend()
        plt.show()
    return peaks