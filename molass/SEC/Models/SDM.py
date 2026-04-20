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

        model_params = kwargs.pop('model_params', None)
        pore_dist = model_params.get('pore_dist', 'mono') if model_params else 'mono'

        if pore_dist == 'lognormal':
            from molass.SEC.Models.SdmEstimator import estimate_sdm_lognormal_from_monopore
            from molass.SEC.Models.SdmOptimizer import optimize_sdm_lognormal_xr_decomposition
            # Two-stage: run mono-pore first for a good starting point
            mono_model_params = dict(model_params) if model_params else {}
            mono_model_params['pore_dist'] = 'mono'
            from molass.SEC.Models.SdmEstimator import estimate_sdm_column_params
            from molass.SEC.Models.SdmOptimizer import optimize_sdm_xr_decomposition
            mono_env = estimate_sdm_column_params(decomposition, **kwargs)
            mono_ccurves = optimize_sdm_xr_decomposition(
                decomposition, mono_env, model_params=mono_model_params, **kwargs)
            env_params = estimate_sdm_lognormal_from_monopore(
                mono_ccurves, decomposition.xr_icurve, **kwargs)
            # Do NOT pass mono-pore k to lognormal — the models have different
            # parameterizations and the same k produces very different shapes.
            # Let the lognormal optimizer use its default k=2.0 (Issue #108).
            ln_model_params = dict(model_params) if model_params else {}
            new_xr_ccurves = optimize_sdm_lognormal_xr_decomposition(
                decomposition, env_params, model_params=ln_model_params, **kwargs)
        else:
            from molass.SEC.Models.SdmEstimator import estimate_sdm_column_params
            from molass.SEC.Models.SdmOptimizer import optimize_sdm_xr_decomposition, adjust_rg_and_poresize
            env_params = estimate_sdm_column_params(decomposition, **kwargs)
            new_xr_ccurves = optimize_sdm_xr_decomposition(
                decomposition, env_params, model_params=model_params, **kwargs)

        if decomposition.uv is None:
            from molass.Decompose.XrOnlyUtils import make_dummy_uv_ccurves
            new_uv_ccurves = make_dummy_uv_ccurves(decomposition.ssd, new_xr_ccurves)
        else:
            from molass.SEC.Models.UvOptimizer import optimize_uv_decomposition
            new_uv_ccurves = optimize_uv_decomposition(decomposition, new_xr_ccurves, **kwargs)
        sdm_decomposition = decomposition.copy_with_new_components(new_xr_ccurves, new_uv_ccurves)

        if pore_dist != 'lognormal':
            rgcurve = kwargs.pop('rgcurve', None)
            adjust_rg_and_poresize(sdm_decomposition, rgcurve=rgcurve)

        if debug:
            import matplotlib.pyplot as plt
            from molass.PlotUtils.DecompositionPlot import plot_elution_curve            
            fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(12, 10))
            fig.suptitle('Optimization Debug Plots')
            if decomposition.uv is not None:
                plot_elution_curve(axes[0, 0], decomposition.uv_icurve, decomposition.uv_ccurves, title="EGH Elution Curves for UV", ylabel="Absorbance")
                plot_elution_curve(axes[1, 0], sdm_decomposition.uv_icurve, sdm_decomposition.uv_ccurves, title="SDM Elution Curves for UV", ylabel="Absorbance")
            plot_elution_curve(axes[0, 1], decomposition.xr_icurve, decomposition.xr_ccurves, title="EGH Elution Curves for XR", ylabel="Scattering Intensity")    
            plot_elution_curve(axes[1, 1], sdm_decomposition.xr_icurve, sdm_decomposition.xr_ccurves, title="SDM Elution Curves for XR", ylabel="Scattering Intensity")
            fig.tight_layout()
        return sdm_decomposition