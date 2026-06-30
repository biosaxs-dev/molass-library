"""
Peaks.RecognizerSpecific.py
"""

def bridge_recognize_peaks(x, y, num_peaks=None, debug=False):
    """
    Recognize peak positions using EghPeeler (library-native implementation).

    Parameters
    ----------
    x : array-like
        The x-coordinates of the curve.
    y : array-like
        The y-coordinates of the curve.
    num_peaks : int, optional
        The number of peaks to recognize.
    debug : bool, optional
        If True, additional debugging information will be printed and plotted.

    Returns
    -------
    list
        A list of indices where peaks are found in the curve.
    """
    from molass.Peaks.EghPeeler import egh_peel
    params_list = egh_peel(x, y, num_components=num_peaks, debug=debug)
    peaks = []
    for h, mu, sigma, tau in params_list:
        peaks.append(int(round(mu - x[0])))
    if debug:
        import numpy as np
        import matplotlib.pyplot as plt
        x = np.asarray(x)
        y = np.asarray(y)
        plt.plot(x, y, label='Curve')
        plt.scatter(x[peaks], y[peaks], color='red', label='Peaks')
        plt.legend()
        plt.show()
    return peaks