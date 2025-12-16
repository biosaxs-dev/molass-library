"""
Bridge.OptimizerInput.py
"""
import logging

class OptimizerInput:
    def __init__(self, legacy=False, in_folder=None, trimming_txt=None):
        self.logger = logging.getLogger(__name__)
        if legacy:
            from molass_legacy.Optimizer.FullOptInput import FullOptInput
            self.logger.info("Using legacy optimizer input.")
            self.legacy_impl = FullOptInput(in_folder=in_folder, trimming_txt=trimming_txt)
        self.legacy = legacy
        self.in_folder = in_folder

    def get_dsets(self):
        if self.legacy:
            return self.legacy_impl.get_dsets()
        else:
            raise NotImplementedError("Non-legacy implementation is not available yet.")
    
    def get_base_curve(self):
        if self.legacy:
            return self.legacy_impl.get_base_curve()
        else:
            raise NotImplementedError("Non-legacy implementation is not available yet.")

    def get_spectral_vectors(self):
        if self.legacy:
            return self.legacy_impl.get_spectral_vectors()
        else:
            raise NotImplementedError("Non-legacy implementation is not available yet.")