"""
Guinier.RgEstimator.py
"""
from molass_legacy.GuinierAnalyzer.SimpleGuinier import SimpleGuinier
from .SimpleFallback import SimpleFallback

class RgEstimator(SimpleGuinier):
    def __init__(self, data):
        super().__init__(data)
        if self.Rg is None or self.Rg == 0:
            try:
                fallback = SimpleFallback(data)
                result = fallback.estimate()
                self.Rg = result['Rg']
                self.Iz = result['I0']
                self.guinier_start = result['q_start']
                self.guinier_stop = result['q_stop']
                self.min_q = result['q_min']
                self.max_q = result['q_max']
            except Exception:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("Fallback Rg estimation failed.", exc_info=True)