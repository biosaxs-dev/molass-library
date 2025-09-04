"""
SEC.Models.EDM.py
"""
class EDM:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def optimize_decomposition(self, decomposition, **kwargs):
        # Implement optimization logic here
        debug = kwargs.get('debug', False)
        if debug:
            from importlib import reload
            import molass.SEC.Models.EdmEstimator
            reload(molass.SEC.Models.EdmEstimator)
            import molass.SEC.Models.EdmOptimizer
            reload(molass.SEC.Models.EdmOptimizer)
            import molass.SEC.Models.UvOptimizer
            reload(molass.SEC.Models.UvOptimizer)
        from molass.SEC.Models.EdmEstimator import estimate_edm_init_params
        from molass.SEC.Models.EdmOptimizer import optimize_edm_xr_decomposition
        from molass.SEC.Models.UvOptimizer import optimize_uv_decomposition

        init_params = estimate_edm_init_params(decomposition, **kwargs)
        new_xr_ccurves = optimize_edm_xr_decomposition(decomposition, init_params, **kwargs)
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