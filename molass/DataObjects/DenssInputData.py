"""
DataObjects.DenssInputData.py

"""

class DenssInputData:
    """
    Class to handle Denss input data.
    """

    def __init__(self, q, I, sigq):
        """
        Initialize the DenssInputData object.

        Parameters
        ----------
        q : array-like
            Array of q values.
        I : array-like
            Array of intensity values.
        sigq : array-like
            Array of uncertainties in q values.
        """
        self.q = q
        self.I = I
        self.sigq = sigq
