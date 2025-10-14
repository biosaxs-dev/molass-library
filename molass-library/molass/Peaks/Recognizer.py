"""
    Peaks.Recognizer.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.signal import find_peaks

MIN_WIDTH = 10

def get_peak_positions(icurve, debug=False, **kwargs):
    """
    Get peak positions from an ICurve object.

    It customizes scipy.signal.find_peaks so that it can find chromatographic peaks properly
    in the curve. By 'properly', it means that it can find not too many, but not too few either.
    That is, without this customization, it tends to find too many (or too few) peaks,
    which is not desirable.

    Parameters
    ----------
    icurve : ICurve
        The input curve from which to find peaks.

    Returns
    -------
    list
        A list of indices where peaks are found in the curve.
    """

    num_peaks = kwargs.get("num_peaks", None)
    x = icurve.x
    y = icurve.y
    if num_peaks is not None:
        from molass.Peaks.RecognizerSpecific import bridge_recognize_peaks
        return bridge_recognize_peaks(x, y, num_peaks=num_peaks, debug=debug)

    m = np.argmax(y)
    max_y = y[m]
    width = MIN_WIDTH
    height = max_y/20
    threshold = None
    distance = 1
    peaks, _ = find_peaks(y,
                          width=width,      # this is required for 20170209/OA_ALD_Fer
                          height=height,
                          # prominence=height,
                          threshold=threshold,
                          distance=distance)
    if len(peaks) == 0:
        # as in 20200630_5, 20200630_6
        print("Try find_peaks with fewer parameters.")
        peaks, _ = find_peaks(y,
                              height=height
                              )
        assert len(peaks) > 0

    if debug:
        from scipy.signal import peak_prominences
        import matplotlib.pyplot as plt
        prominences = peak_prominences(y, peaks)[0]
        print(f"Peaks: {peaks}, prominences: {prominences}")
        fig, ax = plt.subplots()
        ax.set_title("get_peak_positions")
        ax.plot(x, y)
        ax.plot(x[peaks], y[peaks], "o")
        contour_heights = y[peaks] - prominences
        ax.vlines(x=peaks, ymin=contour_heights, ymax=y[peaks], color="C2")
        plt.show()

    return list(peaks)