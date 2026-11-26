"""
Testing module for molass library.
"""
from .PlotControl import (
    plot_controller, show_or_save, is_interactive, 
    control_matplotlib_plot, suppress_numerical_warnings,
    configure_for_test  # Backward compatibility
)
from .HeadlessPeakEditor import draw_scores_headless
from .Simulator import Species, simulate_ssd, continuum_species, tail_shape, fold_unfold_shape
from .Sample4Like import simulate_sample4_like, sample4_like_species
from .Tiny import simulate_tiny
from .Interparticle import (interparticle_frames, InterparticleFrames, hard_sphere_B, sphere_form_factor, debye_form_factor,
                            ellipsoid_form_factor, scale_axes_to_rg, effective_radius, ellipsoid_excluded_volume)

__all__ = [
    'plot_controller', 'show_or_save', 'is_interactive', 
    'control_matplotlib_plot', 'suppress_numerical_warnings',
    'configure_for_test',  # Backward compatibility
    'draw_scores_headless',
    'Species', 'simulate_ssd', 'continuum_species', 'tail_shape', 'fold_unfold_shape',
    'simulate_sample4_like', 'sample4_like_species', 'simulate_tiny',
    'interparticle_frames', 'InterparticleFrames', 'hard_sphere_B', 'sphere_form_factor', 'debye_form_factor',
    'ellipsoid_form_factor', 'scale_axes_to_rg', 'effective_radius', 'ellipsoid_excluded_volume',
]