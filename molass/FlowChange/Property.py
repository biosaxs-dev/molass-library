"""
Flowchange.Property.py
"""

def possibly_has_flowchange_points(ssd):
    """
    Check if the given ssd has flowchange points.

    Parameters
    ----------
    ssd : object
        The ssd to check.

    Returns
    -------
    bool
        True if the ssd has flowchange points, False otherwise.    
    """

    return ssd.beamlineinfo.name == "PF BL-10C"