"""
Backward.RgDiffRatios.py

Modified from molass_legacy.QuickAnalysis.RgDiffRatios
"""
import logging
from molass_legacy.QuickAnalysis.RgDiffRatios import RgDiffRatios as LegacyRgDiffRatios

class SdProxy:
    """
    A proxy class for SecSaxsData, which is used to hold the necessary data for RgDiffRatios.

    Attributes
    ----------
    ssd : SecSaxsData
        The SecSaxsData object.
    xr_curve : Curve
        The XR curve object.
    paired_ranges : list of tuples
        A list of tuples containing paired range data.
    """
    def __init__(self, decomposition):
        """
        Initialize the proxy with a decomposition object.
        
        Parameters
        ----------
        decomposition : DecompositionProxy
            The decomposition data proxy object.
        """
        self.ssd = decomposition.ssd
        self.xr_curve = decomposition.xr_icurve
        self.paired_ranges = decomposition.get_pairedranges()

    def get_xr_data_separate_ly(self):
        """
        Get the XR data from the SecSaxsData object.

        Returns
        -------
        tuple
            A tuple containing the M, E, qv data and the XR curve.
        """
        xr = self.ssd.xr
        return xr.M, xr.E, xr.qv, self.xr_curve

class RgDiffRatios(LegacyRgDiffRatios):
    """A class for computing RgDiffRatios.

    Attributes
    ----------
    logger : logging.Logger
        The logger for the class.
    sd : SdProxy
        The proxy for SecSaxsData.
    paired_ranges : list of tuples
        A list of tuples containing paired range data.
    """
    def __init__(self, decomposition):
        """
        Initialize the RgDiffRatios object with a decomposition proxy.
        Parameters
        ----------
        decomposition : DecompositionProxy
            The decomposition data proxy object.
        """
        self.logger = logging.getLogger(__name__)
        self.sd = SdProxy(decomposition)
        self.paired_ranges = decomposition.get_pairedranges()
