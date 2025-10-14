"""
SEC.Models.SDM.py
"""
class SDM:
    """
    Stochastic Dispersive Model (SDM) for SEC data analysis.
    """
    def __init__(self, **kwargs):
        """ Initialize the SDM model with given parameters.
        Parameters
        ----------
        kwargs : dict
            Additional parameters for the SDM model.
        """
        self.kwargs = kwargs

    def optimize_decomposition(self, decomposition, **kwargs):
        """ Optimize the given decomposition using the SDM model.

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
        if debug:
            from importlib import reload
            import molass.SEC.Models.SdmEstimator
            reload(molass.SEC.Models.SdmEstimator)
            import molass.SEC.Models.SdmOptimizer
            reload(molass.SEC.Models.SdmOptimizer)
            import molass.SEC.Models.UvOptimizer
            reload(molass.SEC.Models.UvOptimizer)
        from molass.SEC.Models.SdmEstimator import estimate_sdm_column_params
        from molass.SEC.Models.SdmOptimizer import optimize_sdm_xr_decomposition
        from molass.SEC.Models.UvOptimizer import optimize_uv_decomposition

        env_params = estimate_sdm_column_params(decomposition, **kwargs)
        new_xr_ccurves = optimize_sdm_xr_decomposition(decomposition, env_params, **kwargs)
        new_uv_ccurves = optimize_uv_decomposition(decomposition, new_xr_ccurves, **kwargs)
        sdm_decomposition = decomposition.copy_with_new_components(new_xr_ccurves, new_uv_ccurves)

        if debug:
            import matplotlib.pyplot as plt
            from molass.PlotUtils.DecompositionPlot import plot_elution_curve            
            fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(12, 10))
            fig.suptitle('Optimization Debug Plots')
            plot_elution_curve(axes[0, 0], decomposition.uv_icurve, decomposition.uv_ccurves, title="EGH Elution Curves for UV", ylabel="Absorbance")
            plot_elution_curve(axes[0, 1], decomposition.xr_icurve, decomposition.xr_ccurves, title="EGH Elution Curves for XR", ylabel="Scattering Intensity")
            plot_elution_curve(axes[1, 0], sdm_decomposition.uv_icurve, sdm_decomposition.uv_ccurves, title="SDM Elution Curves for UV", ylabel="Absorbance")
            plot_elution_curve(axes[1, 1], sdm_decomposition.xr_icurve, sdm_decomposition.xr_ccurves, title="SDM Elution Curves for XR", ylabel="Scattering Intensity")
            fig.tight_layout()
        return sdm_decomposition