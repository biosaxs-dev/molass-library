"""
Backward.ConcTracker.py

Concentration Tracker for Backward Compatibility
"""

import numpy as np
from molass_legacy._MOLASS.SerialSettings import get_setting
from molass.DataObjects.Curve import Curve

class DecompositionProxy:
    """
    A proxy class for the decomposition data.
    This class is used to hold the decomposition data for legacy support.
    """
    def __init__(self, c_vector, xr_curve):
        self.xr_icurve = xr_curve

        """
        Note that the concentration factor is already applied to c_vector.
        Therefore, this should not be multiplied by the concentration factor again.
        See molass_legacy.SerialAnalyzer.StageExtrapolation.control_extrapolation()
        where ConcTracker is used with adjusted_conc_factor which is 1.
        """
        self.mapped_curve = Curve(xr_curve.x, c_vector)

class ConcTracker:
    def __init__(self, decomposition, conc_factor, datatype, jupyter=False, debug=False):
        self.xr_curve = decomposition.xr_icurve
        self.mp_curve = decomposition.mapped_curve * conc_factor
        self.datatype = datatype
        self.concentrations = []
        self.jupyter = jupyter
        self.debug = debug

    def add_concentration(self, start, stop, c_matrix, conc_dependence=1):
        """
        Add a concentration value to the tracker.
        
        Parameters:
        start (int): Start index for the concentration data.
        stop (int): Stop index for the concentration data.
        c_matrix (np.ndarray): Concentration matrix to be added.
        """
        if not isinstance(c_matrix, np.ndarray):
            raise ValueError("c_matrix must be a numpy ndarray.")
        
        if c_matrix.ndim != 2:
            raise ValueError("c_matrix must be a 2D array.")
        
        if start < 0 or stop <= start:
            raise ValueError("Invalid start and stop indices.")

        self.concentrations.append((start, stop, c_matrix, conc_dependence))

    def plot(self, savepath=None):
        """
        Plot the tracked concentrations.
        This method can be extended to visualize the concentration data.
        """
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots()
        ax.plot(self.mp_curve.x, self.mp_curve.y, label='Mapped Curve', color='C0')
        for start, stop, c_matrix, conc_dependence in self.concentrations:
            x = np.arange(start, stop)
            num_rows_to_plot = c_matrix.shape[0] if conc_dependence == 1 else c_matrix.shape[0]//2
            for i in range(num_rows_to_plot):
                ax.plot(x, c_matrix[i,:], label=f'Component {i+1}')

        ax.set_xlabel('Frames')
        ax.set_ylabel('Concentration')
        ax.set_title('Tracked Concentrations')
        ax.legend()
        fig.tight_layout()
        if self.jupyter:
            plt.show()
        
        if savepath is not None:
            fig.savefig(savepath)
            plt.close(fig)
