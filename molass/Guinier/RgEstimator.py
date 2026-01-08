"""
Guinier.RgEstimator.py
"""
from molass_legacy.GuinierAnalyzer.SimpleGuinier import SimpleGuinier
from .SimpleFallback import SimpleFallback

class RgEstimator(SimpleGuinier):
    def __init__(self, data):
        super().__init__(data)
        if self.Rg == 0:
            fallback = SimpleFallback(data)
            result = fallback.estimate()
            self.Rg = result['Rg']
            self.Iz = result['I0']
            self.guinier_start = result['q_start']
            self.guinier_stop = result['q_stop']
            self.min_q = result['q_min']
            self.max_q = result['q_max']