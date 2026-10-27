"""
Testing module for molass library.
"""
from .PlotControl import (
    plot_controller, show_or_save, is_interactive, 
    control_matplotlib_plot, suppress_numerical_warnings,
    configure_for_test  # Backward compatibility
)
from .HeadlessPeakEditor import draw_scores_headless
from .Simulator import Species, simulate_ssd

__all__ = [
    'plot_controller', 'show_or_save', 'is_interactive', 
    'control_matplotlib_plot', 'suppress_numerical_warnings',
    'configure_for_test',  # Backward compatibility
    'draw_scores_headless',
    'Species', 'simulate_ssd',
]