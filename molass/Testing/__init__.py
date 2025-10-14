"""
Testing module for molass library.
"""
from .PlotControl import (
    plot_controller, show_or_save, is_interactive, 
    control_matplotlib_plot, suppress_numerical_warnings,
    configure_for_test  # Backward compatibility
)

__all__ = [
    'plot_controller', 'show_or_save', 'is_interactive', 
    'control_matplotlib_plot', 'suppress_numerical_warnings',
    'configure_for_test'  # Backward compatibility
]