"""
    PlotUtils.PlotResult.py

    Copyright (c) 2025, SAXS Team, KEK-PF 
"""

class PlotResult:
    def __init__(self, fig, axes, **others):
        self.fig = fig
        self.axes = axes = axes
        self.__dict__.update(others)

    def savefig(self, filename, **kwargs):
        """
        Save the figure to a file.

        See matplotlib.pyplot.savefig for details on the parameters.
        """
        self.fig.savefig(filename, **kwargs)

    def close(self):
        """
        Close the figure.

        This is equivalent to calling plt.close(self.fig) in matplotlib.
        It is useful to free up memory when the figure is no longer needed,
        especially in Jupyter notebooks where figures will appear in output cells.
        """
        import matplotlib.pyplot as plt
        plt.close(self.fig)

    def __str__(self):
        return str(self.__dict__)