"""
    Legacy.BackCompatUtils.py
"""
import numpy as np

class ElutioCurvProxy:
    """A proxy class to provide backward compatibility for ElutioCurve.
    It mimics the interface of ElutioCurve using an instance of Curve.

    Attributes
    ----------
    x : array-like
        The x-values of the curve.
    y : array-like
        The y-values of the curve.
    """
    def __init__(self, icurve):
        """Initialize the ElutioCurvProxy with a Curve instance.
        Parameters
        ----------
        icurve : Curve
            The Curve instance to proxy.
        """
        self.x = icurve.x
        self.y = icurve.y
    
    def get_primarypeak_i(self):
        """Get the index of the primary peak (maximum y-value).

        Returns
        -------
        int
            The index of the primary peak.
        """
        return np.argmax(self.y)