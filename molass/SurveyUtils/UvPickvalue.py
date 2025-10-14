"""
    SurveyUtils.UvPickvalue.py
"""

def get_pickvalue(in_folder, wvector):
    """Determine the UV pickvalue based on the input folder name and wvector.
    
    Parameters
    ----------
    in_folder : str
        The input folder name.
    wvector : array-like
        The wavelength vector.

    Returns
    -------
    pickvalue : float
        The determined pickvalue.
    """
    if in_folder.find('OAGIwyatt_01') >= 0 or in_folder.find('OA_Ald_Fer'):
        pickvalue = 400
    elif in_folder.find('20190315_1') >= 0:
        pickvalue = 550
    else:
        pickvalue = wvector[-5]
    return pickvalue