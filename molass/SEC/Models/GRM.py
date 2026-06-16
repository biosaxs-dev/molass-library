"""
SEC.Models.GRM.py

GRM (General Rate Model) column model class.

Copyright (c) 2026, SAXS Team, KEK-PF
"""


class GRM:
    """
    General Rate Model (GRM) for SEC data analysis.

    Parameters are estimated via moment-matching from LKM (GrmEstimator) and
    then each component's scale is refined by NNLS (GrmOptimizer).

    The rigorous ``optimize_rigorously(model='GRM')`` step uses the G1500
    objective function (molass-legacy) to refine all GRM parameters jointly.

    The GRM accounts for:
    - Axial dispersion (Péclet number Pe)
    - External film mass transfer (k_ext per component)
    - Intraparticle pore diffusion (D_eff, shared)
    - Linear adsorption equilibrium (a_star, via retention factor R)
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def optimize_decomposition(self, decomposition, **kwargs):
        """
        Upgrade an EGH decomposition to use GRM component curves.

        Parameters
        ----------
        decomposition : Decomposition
            Initial EGH decomposition to upgrade.
        R_p : float, optional
            Particle radius [cm].  Default from SerialSettings or 0.0035 cm.
        D_eff : float, optional
            Effective pore diffusivity [cm²/min].  Default 1e3 (film-only limit).
        eps_p : float, optional
            Intraparticle porosity.  Default 0.0 (non-porous).
        eps : float, optional
            Interstitial column porosity.  Default 0.4.
        debug : bool, optional
            Enable verbose output.

        Returns
        -------
        Decomposition
            New decomposition with ``GrmComponentCurve`` objects.
        """
        debug = kwargs.get('debug', False)

        if debug:
            from importlib import reload
            import molass.SEC.Models.GrmEstimator
            reload(molass.SEC.Models.GrmEstimator)
            import molass.SEC.Models.GrmOptimizer
            reload(molass.SEC.Models.GrmOptimizer)
            import molass.SEC.Models.UvOptimizer
            reload(molass.SEC.Models.UvOptimizer)

        from molass.SEC.Models.GrmEstimator import estimate_grm_init_params
        from molass.SEC.Models.GrmOptimizer import optimize_grm_xr_decomposition

        grm_init_params = estimate_grm_init_params(decomposition, **kwargs)
        new_xr_ccurves = optimize_grm_xr_decomposition(
            decomposition, grm_init_params, **kwargs)

        if decomposition.uv is None:
            from molass.Decompose.XrOnlyUtils import make_dummy_uv_ccurves
            new_uv_ccurves = make_dummy_uv_ccurves(decomposition.ssd, new_xr_ccurves)
        else:
            from molass.SEC.Models.UvOptimizer import optimize_uv_decomposition
            new_uv_ccurves = optimize_uv_decomposition(
                decomposition, new_xr_ccurves, **kwargs)

        return decomposition.copy_with_new_components(new_xr_ccurves, new_uv_ccurves)
