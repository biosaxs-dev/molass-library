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

    if ssd.beamlineinfo is None:
        return False
    elif ssd.beamlineinfo.name is None:
        return False

    # return ssd.beamlineinfo.name == "PF BL-10C"
    return ssd.beamlineinfo.name[0:2] == "PF"   # some PF BL-15A2 data also have flowchange points