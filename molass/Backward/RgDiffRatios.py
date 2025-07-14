"""
Backward.RgDiffRatios.py

Modified from molass_legacy.QuickAnalysis.RgDiffRatios
"""
import logging
from molass_legacy.QuickAnalysis.RgDiffRatios import RgDiffRatios as LegacyRgDiffRatios

class SdProxy:
    def __init__(self, decomposition):
        self.ssd = decomposition.ssd
        self.xr_curve = decomposition.xr_icurve
        self.paired_ranges = decomposition.get_pairedranges()

    def get_xr_data_separate_ly(self):
        xr = self.ssd.xr
        return xr.M, xr.E, xr.qv, self.xr_curve

class RgDiffRatios(LegacyRgDiffRatios):
    def __init__(self, decomposition):
        self.logger = logging.getLogger(__name__)
        self.sd = SdProxy(decomposition)
        self.paired_ranges = decomposition.get_pairedranges()
