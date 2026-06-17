"""
SEC.Models.EDM.py
"""
class EDM:
    """
    Equilibrium Dispersive Model (EDM) for SEC data analysis.
    """
    def __init__(self, **kwargs):
        """ Initialize the EDM model with given parameters.

        Parameters
        ----------
        kwargs : dict
            Additional parameters for the EDM model.
        """
        self.kwargs = kwargs

    def optimize_decomposition(self, decomposition, **kwargs):
        """ Optimize the given decomposition using the EDM model.

        Parameters
        ----------
        decomposition : Decomposition
            The initial decomposition to be optimized.
        kwargs : dict
            Additional parameters for the optimization process.
        Returns
        -------
        Decomposition
            The optimized decomposition.
        """
        debug = kwargs.get('debug', False)
        # Merge constructor kwargs (e.g. shared_column set by ModelFactory for CEDM)
        # with call-time kwargs; call-time values take precedence.
        merged = {**self.kwargs, **kwargs}
        kwargs = merged
        if debug:
            from importlib import reload
            import molass.SEC.Models.EdmEstimator
            reload(molass.SEC.Models.EdmEstimator)
            import molass.SEC.Models.EdmOptimizer
            reload(molass.SEC.Models.EdmOptimizer)
            import molass.SEC.Models.UvOptimizer
            reload(molass.SEC.Models.UvOptimizer)
        from molass.SEC.Models.EdmEstimator import estimate_edm_init_params
        from molass.SEC.Models.EdmOptimizer import optimize_edm_xr_decomposition, refine_edm_per_component
        from molass.SEC.Models.UvOptimizer import optimize_uv_decomposition

        init_params = estimate_edm_init_params(decomposition, **kwargs)
        # Pass 1 (heavy): full shared-column optimisation — finds (t0, u, e, Dz, a, b, cinj).
        new_xr_ccurves = optimize_edm_xr_decomposition(decomposition, init_params, **kwargs)
        # Pass 2 (lighter, optional): fix shared column (t0, u, e, Dz), refine per-component (a, b, cinj).
        # Beneficial for SAMPLE2/SAMPLE3 (massive fv improvement) but regresses SAMPLE4 (4-comp).
        # SAMPLE4 regression root cause: unconstrained b → EDM overflow for 4-component systems.
        # Enable via refine_per_component=True once b-bounds / overflow handling is improved.
        if kwargs.get('refine_per_component', False):
            x, y = decomposition.xr_icurve.get_xy()
            new_xr_ccurves = refine_edm_per_component(new_xr_ccurves, x, y, **kwargs)
        if decomposition.uv is None:
            new_uv_ccurves = None
        else:
            new_uv_ccurves = optimize_uv_decomposition(decomposition, new_xr_ccurves, **kwargs)
        edm_decomposition = decomposition.copy_with_new_components(new_xr_ccurves, new_uv_ccurves)

        if debug:
            import matplotlib.pyplot as plt
            from molass.PlotUtils.DecompositionPlot import plot_elution_curve            
            fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(12, 10))
            fig.suptitle('Optimization Debug Plots')
            plot_elution_curve(axes[0, 0], decomposition.uv_icurve, decomposition.uv_ccurves, title="EGH Elution Curves for UV", ylabel="Absorbance")
            plot_elution_curve(axes[0, 1], decomposition.xr_icurve, decomposition.xr_ccurves, title="EGH Elution Curves for XR", ylabel="Scattering Intensity")
            plot_elution_curve(axes[1, 0], edm_decomposition.uv_icurve, edm_decomposition.uv_ccurves, title="EDM Elution Curves for UV", ylabel="Absorbance")
            plot_elution_curve(axes[1, 1], edm_decomposition.xr_icurve, edm_decomposition.xr_ccurves, title="EDM Elution Curves for XR", ylabel="Scattering Intensity")
            fig.tight_layout()
        return edm_decomposition