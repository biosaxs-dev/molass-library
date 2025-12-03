"""
Rigorous.RunInfo.py
"""

class RunInfo:
    def __init__(self, optimizer, dsets, init_params):
        self.optimizer = optimizer
        self.dsets = dsets
        self.init_params = init_params