"""
Backward.ConcTracker.py

Concentration Tracker for Backward Compatibility
"""

import logging
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
    """
    A class to track concentrations for backward compatibility.
    This class is used to track concentrations in a way that is compatible with older versions of the MOLASS library.

    Attributes
    ----------
    xr_curve : Curve
        The XR curve object.
    mp_curve : Curve
        The mapped curve object.
    datatype : str
        The type of data being processed (e.g., "i", "d", etc.).
    concentrations : list of tuples
        A list of tuples containing concentration data.
    jupyter : bool
        A flag indicating whether the code is running in a Jupyter notebook.
    debug : bool
        A flag indicating whether to enable debug mode.
    """
    def __init__(self, decomposition, conc_factor, datatype, jupyter=False, debug=False):
        """
        Initializes the ConcTracker object with the given parameters.

        Parameters
        ----------
        decomposition : DecompositionProxy
            The decomposition data proxy object.
        conc_factor : float
            The concentration factor to be applied to the concentration data.
        datatype : str
            The type of data being processed (e.g., "i", "d", etc.).
        jupyter : bool, optional
            A flag indicating whether the code is running in a Jupyter notebook.
            Default is False.
        debug : bool, optional
            A flag indicating whether to enable debug mode.
            Default is False.
        """

        self.logger = logging.getLogger(__name__)
        self.xr_curve = decomposition.xr_icurve
        self.mp_curve = decomposition.mapped_curve * conc_factor
        self.datatype = datatype
        self.concentrations = []
        self.jupyter = jupyter
        self.debug = debug
        self.logger.info(f'Initialized ConcTracker with datatype={datatype}, jupyter={jupyter}, debug={debug}')

    def add_concentration(self, start, stop, c_matrix, conc_dependence=1):
        """
        Add a concentration value to the tracker.

        Parameters
        ----------
        start : int
            The starting index of the concentration data.
        stop : int
            The ending index of the concentration data.
        c_matrix : np.ndarray
            The concentration data matrix.
        conc_dependence : int, optional
            The concentration dependence (1 or 2).
            Default is 1.
        """
        if not isinstance(c_matrix, np.ndarray):
            raise ValueError("c_matrix must be a numpy ndarray.")
        
        if c_matrix.ndim != 2:
            raise ValueError("c_matrix must be a 2D array.")
        
        if start < 0 or stop <= start:
            raise ValueError("Invalid start and stop indices.")

        self.concentrations.append((start, stop, c_matrix, conc_dependence))
        self.logger.info(f'Added concentration from {start} to {stop} with shape {c_matrix.shape} and conc_dependence={conc_dependence}')

    def plot(self, savepath=None):
        """
        Plot the tracked concentrations.
        This method can be extended to visualize the concentration data.

        Parameters
        ----------
        savepath : str, optional
            The path to save the plot. If None, the plot will not be saved.
            Default is None.
            
        Returns
        -------
        None
        """
        import matplotlib.pyplot as plt
        
        x = self.xr_curve.x
        fig, axes = plt.subplots(ncols=2, figsize=(12, 5))
        fig.suptitle('Tracked Concentrations')
        for k, ax in enumerate(axes):
            ax.set_title(f'With Rank {k+1}')
            ax.set_xlabel('Frames')
            ax.set_ylabel('Concentration')
            ax.plot(self.mp_curve.x, self.mp_curve.y, label='Mapped Curve', color='C0')
        for start, stop, c_matrix, conc_dependence in self.concentrations:
            self.logger.info(f'Plotting concentration from {start} to {stop} with shape {c_matrix.shape} and conc_dependence={conc_dependence}')
            ax = axes[conc_dependence - 1]
            x_ = x[start:stop]
            num_rows_to_plot = c_matrix.shape[0] if conc_dependence == 1 else c_matrix.shape[0]//2
            for i in range(num_rows_to_plot):
                ax.plot(x_, c_matrix[i,:], label=f'Component {i+1}')

        for ax in axes: 
            ax.legend()
        fig.tight_layout()
        if self.jupyter:
            plt.show()
        
        if savepath is not None:
            fig.savefig(savepath)
            plt.close(fig)
