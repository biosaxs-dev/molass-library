"""
    PlotUtils.PlotResult.py

    Copyright (c) 2025, SAXS Team, KEK-PF 
"""

class PlotResult:
    def __init__(self, fig, axes, **others):
        self.fig = fig
        self.axes = axes = axes
        self.__dict__.update(others)

    def __str__(self):
        return str(self.__dict__)