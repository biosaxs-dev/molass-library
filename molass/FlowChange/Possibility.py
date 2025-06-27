"""
Flowchange.Possibility.py
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

    name = ssd.get_beamline_name()
    if name is None:
        return False

    return name[0:2] == "PF"    # some PF BL-15A2 data also have flowchange points