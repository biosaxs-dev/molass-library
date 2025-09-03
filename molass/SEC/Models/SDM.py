"""
SEC.Models.SDM.py
"""
from molass_legacy.Models.Stochastic.DispersivePdf import dispersive_monopore_pdf
from molass.PlotUtils.DecompositionPlot import plot_elution_curve

class SDM:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def optimize_decomposition(self, decomposition, **kwargs):
        # Implement optimization logic here
        debug = kwargs.get('debug', False)
        if debug:
            from importlib import reload
            import molass.SEC.Models.SdmEstimator
            reload(molass.SEC.Models.SdmEstimator)
            import molass.SEC.Models.SdmOptimizer
            reload(molass.SEC.Models.SdmOptimizer)
        from molass.SEC.Models.SdmEstimator import estimate_env_params
        from molass.SEC.Models.SdmOptimizer import optimize_sdm_decomposition_impl

        env_params = estimate_env_params(decomposition, **kwargs)
        sdm_decomposition = optimize_sdm_decomposition_impl(decomposition, env_params, **kwargs)

        if debug:
            import matplotlib.pyplot as plt            
            fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(12, 10))
            fig.suptitle('Optimization Debug Plots')
            plot_elution_curve(axes[0, 0], decomposition.uv_icurve, decomposition.uv_ccurves, title="EGH Elution Curves for UV", ylabel="Absorbance")
            plot_elution_curve(axes[0, 1], decomposition.xr_icurve, decomposition.xr_ccurves, title="EGH Elution Curves for XR", ylabel="Scattering Intensity")
            plot_elution_curve(axes[1, 0], sdm_decomposition.uv_icurve, sdm_decomposition.uv_ccurves, title="SDM Elution Curves for UV", ylabel="Absorbance")
            plot_elution_curve(axes[1, 1], sdm_decomposition.xr_icurve, sdm_decomposition.xr_ccurves, title="SDM Elution Curves for XR", ylabel="Scattering Intensity")
            fig.tight_layout()
        return sdm_decomposition