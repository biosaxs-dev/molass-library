"""
DataUtils.Outliers.py
"""
import numpy as np

def remove_outliers(values, repeat=1):
    """
    Remove outliers from a dataset.

    Parameters
    ----------
    values : array-like

    repeat : int
        The number of times to repeat the outlier removal process.

    Returns
    -------
    cleaned : array-like
        The input array with outliers removed.
    """
    if len(values) == 0:
        return values

    # Convert to a NumPy array for easier manipulation
    data = np.asarray(values)
    cleaned = data.copy()

    for _ in range(repeat):
        # Compute the mean and standard deviation
        mean = np.nanmean(cleaned)
        std = np.nanstd(cleaned)

        # Define a threshold for identifying outliers
        threshold = 3 * std

        # Remove outliers
        cleaned[np.abs(cleaned - mean) >= threshold] = np.nan

    return cleaned