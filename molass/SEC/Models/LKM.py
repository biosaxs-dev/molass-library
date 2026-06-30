"""
SEC.Models.LKM.py

LKM (Lumped Kinetic Model) column model class.

Copyright (c) 2024, SAXS Team, KEK-PF
"""


class LKM:
    """
    Lumped Kinetic Model (LKM) for SEC data analysis.

    Parameters are estimated via moment-matching (LkmEstimator) and then
    each component's scale is refined by NNLS (LkmOptimizer).

    The rigorous ``optimize_rigorously()`` step uses the G1400 objective
    function (molass-legacy) to refine all LKM parameters jointly.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def optimize_decomposition(self, decomposition, **kwargs):
        """
        Upgrade an EGH decomposition to use LKM component curves.

        Parameters
        ----------
        decomposition : Decomposition
            Initial EGH decomposition to upgrade.
        kwargs : dict
            Passed through to estimator and optimizer.
            ``debug=True`` enables verbose output.

        Returns
        -------
        Decomposition
            New decomposition with ``LkmComponentCurve`` objects.
        """
        debug = kwargs.get('debug', False)

        if debug:
            from importlib import reload
            import molass.SEC.Models.LkmEstimator
            reload(molass.SEC.Models.LkmEstimator)
            import molass.SEC.Models.LkmOptimizer
            reload(molass.SEC.Models.LkmOptimizer)
            import molass.SEC.Models.UvOptimizer
            reload(molass.SEC.Models.UvOptimizer)

        from molass.SEC.Models.LkmEstimator import estimate_lkm_init_params
        from molass.SEC.Models.LkmOptimizer import optimize_lkm_xr_decomposition

        lkm_init_params = estimate_lkm_init_params(decomposition, **kwargs)
        new_xr_ccurves = optimize_lkm_xr_decomposition(
            decomposition, lkm_init_params, **kwargs)

        if decomposition.uv is None:
            from molass.Decompose.XrOnlyUtils import make_dummy_uv_ccurves
            new_uv_ccurves = make_dummy_uv_ccurves(decomposition.ssd, new_xr_ccurves)
        else:
            from molass.SEC.Models.UvOptimizer import optimize_uv_decomposition
            new_uv_ccurves = optimize_uv_decomposition(
                decomposition, new_xr_ccurves, **kwargs)

        return decomposition.copy_with_new_components(new_xr_ccurves, new_uv_ccurves)
