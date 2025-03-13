"""
    Peaks.Recognizer.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.signal import find_peaks

MIN_WIDTH = 10

def get_peak_positions(icurve, debug=False):
    x = icurve.x
    y = icurve.y
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