"""
    DataUtils.XrLoader.py
"""
from glob import glob
import numpy as np

def load_xr(folder_path):
    """
    Load X-ray scattering data from a folder containing .dat files.
    Parameters
    ----------
    folder_path : str
        Path to the folder containing .dat files.
    Returns
    -------
    xr_array : np.ndarray
        3D array containing the X-ray scattering data.
    Notes
    -----
    The function assumes that each .dat file contains data in a format compatible with np.loadtxt.
    The first dimension corresponds to the number of files, the second to the number of points, and the third to the data columns.
    """
    input_list = []
    datafiles = []
    for path in sorted(glob(folder_path + "/*.dat")):
        input_list.append(np.loadtxt(path))
        datafiles.append(path)
    xr_array = np.array(input_list)
    return xr_array, datafiles

def xr_remove_bubbles(xr_array, logger=None, debug=False):
    from molass.DataObjects.Curve import create_icurve
    from molass.DataUtils.AnomalyHandlers import bubble_check_impl, remove_bubbles_impl
    qv = xr_array[0,:,0]
    xrM = xr_array[:,:,1].T
    x = np.arange(xrM.shape[1])
    icurve = create_icurve(x, xrM, qv, pickvalue=0.02)
    bubbles = bubble_check_impl(icurve.y)

    if debug:
        from copy import deepcopy
        print(f"bubbles: {bubbles}")
        icurve_orig = deepcopy(icurve)

    if len(bubbles) > 0:
        excluded_set = set()
        remove_bubbles_impl(xr_array, bubbles, excluded_set)
        if logger is None:
            print("bubbles have been removed at %s" % bubbles)
        else:
            logger.warning("bubbles have been removed at %s", bubbles)

    if debug:
        import matplotlib.pyplot as plt
        xrM_ = xr_array[:,:,1].T
        icurve_ = create_icurve(x, xrM_, qv, pickvalue=0.02)
        fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(12, 5))
        ax1.plot(*icurve_orig.get_xy())
        ax2.plot(*icurve_.get_xy())
        plt.show()

def load_xr_with_options(folder_path, remove_bubbles=False, logger=None, debug=False):
    xr_array, datafiles = load_xr(folder_path)
    if remove_bubbles:
        xr_remove_bubbles(xr_array, logger=logger, debug=debug)
    return xr_array, datafiles