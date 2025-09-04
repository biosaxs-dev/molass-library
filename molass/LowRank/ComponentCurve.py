"""
    LowRank.ComponentCurve.py
"""
import numpy as np
from molass.SEC.Models.Simple import egh

class ComponentCurve:
    """
    A class to represent a component curve.
    """

    def __init__(self, x, params):
        """
        """
        self.x = x
        self.params = np.asarray(params)
        self.moment = None

    def get_y(self):
        """
        """
        return egh(self.x, *self.params)

    def get_xy(self):
        """
        """
        x = self.x
        return x, egh(x, *self.params)

    def get_moment(self):
        if self.moment is None:
            from molass.Stats.Moment import Moment
            x, y = self.get_xy()
            self.moment = Moment(x, y)
        return self.moment

    def get_params(self):
        """
        Returns the parameters of the component curve.
        """
        return self.params

    def get_peak_top_x(self):
        """
        Returns the x value at the peak top.
        """
        return self.params[1]   # peak position in EGH model, note that this in valid only for EGH model