"""
    LowRank.LowRankInfo.py

    This module contains the class LowRankInfo, which is used to store information
    about the components of a SecSaxsData, which is mathematically interpreted as
    a low rank approximation of a matrix.
"""
from importlib import reload
import numpy as np

class Decomposition:
    """
    A class to store the result of decomposition which is a low rank approximation.

    The result includes both components of X-ray and UV data and their associated information.

    Attributes
    ----------
    ssd : SecSaxsData
        The SecSaxsData object from which the decomposition was performed.
    xr : XrData
        The XrData object from the SecSaxsData.
    xr_icurve : Curve
        The i-curve used for the decomposition of the X-ray data.
    xr_ccurves : list of Curve
        The component curves for the X-ray data.
    xr_ranks : list of int or None
        The ranks for each component of the X-ray data. If None, default ranks are used.
    uv : UvData
        The UvData object from the SecSaxsData.
    uv_icurve : Curve
        The i-curve used for the decomposition of the UV data.
    uv_ccurves : list of Curve
        The component curves for the UV data.
    uv_ranks : list of int or None
        The ranks for each component of the UV data. If None, default ranks are used.
    mapping : MappingInfo
        The mapping information between the X-ray and UV data.
    mapped_curve : MappedCurve or None
        The mapped curve from the X-ray to UV domain. If None, it can be computed when needed.
    paired_ranges : list of PairedRange or None
        The paired ranges for the X-ray and UV data. If None, it can be computed when needed.
    num_components : int
        The number of components in the decomposition.
    """

    def __init__(self, ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, mapped_curve=None, paired_ranges=None, **kwargs):
        """
        Initialize the Decomposition object.

        Parameters
        ----------
        ssd : SecSaxsData
            The SecSaxsData object from which the decomposition was performed.
        xr_icurve : Curve
            The i-curve used for the decomposition of the X-ray data.
        xr_ccurves : list of Curve
            The component curves for the X-ray data.
        uv_icurve : Curve
            The i-curve used for the decomposition of the UV data.
        uv_ccurves : list of Curve
            The component curves for the UV data.
        mapped_curve : MappedCurve, optional
            The mapped curve from the X-ray to UV domain. If None, it can be computed when needed.
        paired_ranges : list of PairedRange, optional
            The paired ranges for the X-ray and UV data. If None, it can be computed when needed.
        kwargs : dict, optional
            Additional keyword arguments (not used).
        """
        if uv_ccurves is None:
            pass
        else:
            assert len(xr_ccurves) == len(uv_ccurves)  
        self.num_components = len(xr_ccurves)
        self.ssd = ssd

        self.xr = ssd.xr
        self.xr_icurve = xr_icurve
        self.xr_ccurves = xr_ccurves
        self.xr_ranks = None

        self.uv = ssd.uv
        self.uv_icurve = uv_icurve
        self.uv_ccurves = uv_ccurves
        self.uv_ranks = None
 
        self.mapping = ssd.get_mapping()
        self.mapped_curve = mapped_curve
        self.paired_ranges = paired_ranges

        self.guinier_objects = None
        self.bounded_lrf_info = None
        self.model = xr_ccurves[0].model

    def copy_with_new_components(self, xr_ccurves, uv_ccurves):
        """
        Create a new Decomposition with new component curves.

        Parameters
        ----------
        xr_ccurves : list of Curve
            The new component curves for the X-ray data.
        uv_ccurves : list of Curve
            The new component curves for the UV data.

        Returns
        -------
        Decomposition
            A new Decomposition object with the specified component curves.
        """
        return Decomposition(self.ssd, self.xr_icurve, xr_ccurves, self.uv_icurve, uv_ccurves, self.mapped_curve, self.paired_ranges)

    @property
    def xr_components(self):
        """Alias for ``xr_ccurves`` — the XR component curves."""
        return self.xr_ccurves

    @property
    def uv_components(self):
        """Alias for ``uv_ccurves`` — the UV component curves."""
        return self.uv_ccurves

    def get_num_components(self):
        """
        Get the number of components.

        Returns
        -------
        int
            The number of components in the decomposition.
        """
        return self.num_components

    def get_guinier_objects(self, debug=False):
        """
        Get the list of Guinier objects for the XR components.

        Returns
        -------
        list of Guinier
            The list of Guinier objects for each XR component.
        """
        if self.guinier_objects is None:
            xr_components = self.get_xr_components(debug=debug)
            self.guinier_objects = [c.get_guinier_object() for c in xr_components]
        return self.guinier_objects

    def get_rgs(self):
        """
        Get the list of Rg values for the XR components.

        Returns
        -------
        rgs : list of float, length n_components
            Radius of gyration in **Ångströms (Å)** for each XR component,
            in the same order as ``get_xr_components()``.
            If Guinier fitting fails for a component, ``float('nan')`` is
            returned for that position (never ``None``), so the result is
            always safe to use in numeric / numpy operations.

            Guard pattern::

                import math
                for i, rg in enumerate(decomp.get_rgs()):
                    if math.isnan(rg):
                        print(f"Component {i+1}: Guinier fit failed")
                    else:
                        print(f"Component {i+1}: Rg = {rg:.2f} Å")
        """
        return [sv.Rg if sv.Rg is not None else float('nan')
                for sv in self.get_guinier_objects()]

    def get_rg_curve(self):
        """Compute the per-frame Rg curve from the raw XR data.

        Runs a Guinier fit on every elution frame independently and returns
        the results as an ``RgCurve`` object.  This is useful for assessing
        whether a peak is a pure single-component species (flat Rg vs. frame)
        or a heterogeneous mixture (varying Rg).

        .. note::
            This can be slow for large datasets because it fits one Guinier
            region per frame.

        Returns
        -------
        rgcurve : molass.Guinier.RgCurve.RgCurve
            An ``RgCurve`` with attributes:

            - ``.x`` — frame indices (integer array)
            - ``.y`` — Rg values in Å; ``NaN`` where Guinier fit failed
            - ``.scores`` — Guinier fit quality scores (0–1)

        Examples
        --------
        ::

            rgcurve = decomp.get_rg_curve()
            import matplotlib.pyplot as plt
            plt.plot(rgcurve.x, rgcurve.y, '.')
            plt.xlabel("Frame")
            plt.ylabel("Rg (Å)")
            plt.title("Rg vs. elution frame")
            plt.show()
        """
        return self.xr.compute_rgcurve()

    def get_P_at(self, q_target, normalize=False):
        """Return the XR scattering matrix P interpolated onto *q_target*.

        Parameters
        ----------
        q_target : array-like, shape (m,)
            Target q-values in Å⁻¹.
        normalize : bool, optional
            If ``True``, each component column is divided by its maximum so
            that all columns peak at 1.  Default ``False``.

        Returns
        -------
        P_interp : np.ndarray, shape (m, n_components)
            Scattering matrix P evaluated at *q_target*.
        """
        from molass.LowRank.AlignDecompositions import get_P_at
        return get_P_at(self, q_target, normalize=normalize)

    def component_quality_scores(self):
        """
        Compute a per-component reliability score in [0, 1].

        Scores blend Rg distinctiveness (70 %) and area proportion (30 %).
        A score of 0.0 means Guinier fitting failed or Rg is indistinguishable
        from another component's.  A score near 1.0 means the component is
        well-separated in Rg and carries a non-trivial fraction of the signal.

        Returns
        -------
        scores : list of float
            Reliability score for each component, in the same order as
            ``get_rgs()`` and ``get_proportions()``.

        See Also
        --------
        is_component_reliable : threshold-based boolean version.

        Examples
        --------
        ::

            scores = decomp.component_quality_scores()
            for i, s in enumerate(scores):
                print(f"Component {i+1}: reliability = {s:.2f}")
        """
        from molass.LowRank.ComponentReliability import component_quality_scores
        return component_quality_scores(self)

    def is_component_reliable(self, index, threshold=0.5):
        """
        Return ``True`` if component *index* has a quality score ≥ *threshold*.

        Parameters
        ----------
        index : int
            Zero-based component index.
        threshold : float, optional
            Minimum score considered reliable.  Default 0.5.

        Returns
        -------
        bool

        Examples
        --------
        ::

            if not decomp.is_component_reliable(1):
                print("Component 2 may be a noise artifact.")
        """
        from molass.LowRank.ComponentReliability import is_component_reliable
        return is_component_reliable(self, index, threshold=threshold)

    def plot_components(self, **kwargs):
        """decomposition.plot_components(title=None, fig=None, axes=None, **kwargs)

        Plot the components.

        Parameters
        ----------
        title : str, optional
            If specified, add a super title to the plot.
        fig : matplotlib.figure.Figure, optional
            An existing Figure to draw into. If ``None`` (default), a new
            figure is created automatically.
        axes : array-like of shape (2, 3), optional
            A 2×3 array of Axes to draw into. Must be provided together with
            ``fig`` when injecting into an existing subplot grid. If ``None``
            (default), axes are created automatically inside *fig*.

            Expected layout::

                axes[0, 0]  UV elution curves
                axes[0, 1]  UV absorbance curves
                axes[0, 2]  (UV spare / unused)
                axes[1, 0]  XR elution curves
                axes[1, 1]  XR scattering curves (log scale)
                axes[1, 2]  XR Guinier plot  ← Kratky is omitted when axes are injected

            .. note::
                When both *fig* and *axes* are provided the caller is
                responsible for creating axes with compatible geometry.

        Returns
        -------
        result : PlotResult
            A PlotResult object which contains the following attributes.
            
            - fig: The matplotlib Figure object.
            - axes: A 2×3 array of Axes objects.
        """
        debug = kwargs.get('debug', False)
        if debug:
            from importlib import reload
            import molass.PlotUtils.DecompositionPlot
            reload(molass.PlotUtils.DecompositionPlot)
        from molass.PlotUtils.DecompositionPlot import plot_components_impl, ALLOWED_KEYS
        for key in kwargs.keys():
            if key not in ALLOWED_KEYS:
                raise ValueError(f"Invalid key: {key}. Allowed keys are: {ALLOWED_KEYS}")
        return plot_components_impl(self, **kwargs)

    def update_xr_ranks(self, ranks, debug=False):
        """
        Update the ranks for the X-ray data.

        Default ranks are one for each component which means that interparticle interactions are not considered.
        This method allows the user to set different ranks for each component.

        Parameters
        ----------
        ranks : list of int
            The ranks for each component.

        Returns
        -------
        None
        """
        self.xr_ranks = ranks

    def get_xr_matrices(self, debug=False):
        """
        Get the factorized matrices for the X-ray (SAXS) data.

        Parameters
        ----------
        debug : bool, optional
            If True, enable debug mode.

        Returns
        -------
        M : np.ndarray, shape (n_q, n_frames)
            Measured scattering intensity matrix.
            Rows are q-points; columns are elution frames.
        C : np.ndarray, shape (n_components, n_frames)
            Elution curves (concentration profiles) for each component.
            Each row is one component's elution curve over frames.
        P : np.ndarray, shape (n_q, n_components)
            Scattering profiles (form factors) for each component.
            Each **column** is one component's P(q) in absolute or
            relative intensity units (matching the scale of M).
        Pe : np.ndarray, shape (n_q, n_components)
            Estimated error (standard deviation) on P,
            propagated from the measurement error matrix.

        Notes
        -----
        The q-values corresponding to the n_q rows are stored in
        ``decomp.xr.qv`` (shape ``(n_q,)``, units Å⁻¹).

        Example
        -------
        ::

            M, C, P, Pe = decomp.get_xr_matrices()
            # P[:, 0]  →  scattering profile of component 1
            # C[0, :]  →  elution curve of component 1
        """
        if debug:
            from importlib import reload
            import molass.LowRank.LowRankInfo
            reload(molass.LowRank.LowRankInfo)
        from molass.LowRank.LowRankInfo import compute_lowrank_matrices

        xr = self.xr

        # Step 1: naïve factorization (compute_lowrank_matrices unchanged)
        M_, C_, P_, Pe = compute_lowrank_matrices(
            xr.M, self.xr_ccurves, xr.E, self.xr_ranks, debug=debug)

        # Step 2: apply bounded LRF if any component is rank-2
        ranks = self.xr_ranks or [1] * self.num_components
        has_rank2 = any(r == 2 for r in ranks)

        if has_rank2:
            from molass.Guinier.RgEstimator import RgEstimator

            # Step 2a: pre-populate guinier_objects from naïve P
            if self.guinier_objects is None:
                guinier_objects = []
                for i in range(self.num_components):
                    jcurve_array = np.array([xr.qv, P_[:, i], Pe[:, i]]).T
                    guinier_objects.append(RgEstimator(jcurve_array))
                self.guinier_objects = guinier_objects

            # Step 2b: reconstruct full C and P (including c² rows/B columns)
            cy_list = [c.get_xy()[1] for c in self.xr_ccurves]
            for k, r in enumerate(ranks):
                if r > 1:
                    cy_list.append(cy_list[k] ** r)
            C_full = np.array(cy_list)
            P_full = M_ @ np.linalg.pinv(C_full)

            # Step 2c: apply bounded LRF
            if debug:
                from importlib import reload
                import molass.LowRank.BoundedLrf
                reload(molass.LowRank.BoundedLrf)
            from molass.LowRank.BoundedLrf import apply_bounded_lrf
            P_, bounded_info = apply_bounded_lrf(
                xr.qv, P_full, C_full, ranks, self.guinier_objects)
            self.bounded_lrf_info = bounded_info

            # Step 2d: re-propagate error for corrected P
            if xr.E is not None:
                from molass.LowRank.ErrorPropagate import compute_propagated_error
                Pe = compute_propagated_error(M_, P_, xr.E)

        return M_, C_, P_, Pe

    def get_xr_components(self, debug=False):
        """
        Get the per-component objects for the X-ray (SAXS) data.

        Parameters
        ----------
        debug : bool, optional
            If True, enable debug mode.

        Returns
        -------
        components : list of :class:`~molass.LowRank.Component.XrComponent`, length n_components
            One ``XrComponent`` per decomposed component, in component order.

            Each ``XrComponent`` exposes:

            - ``get_guinier_object()`` → Guinier fit result (Rg, I0, fit range)
            - ``get_jcurve_array()`` → ``np.ndarray`` shape ``(n_q, 3)``:
              columns are ``[q, P(q), Pe(q)]`` in Å⁻¹ and intensity units.
            - ``icurve_array`` → ``np.ndarray`` shape ``(2, n_frames)``:
              rows are ``[frame_x, elution_y]``.
            - ``compute_area()`` → scalar, integrated elution area.
        """
        if debug:
            from importlib import reload
            import molass.LowRank.Component
            reload(molass.LowRank.Component)
        from molass.LowRank.Component import XrComponent

        xr_matrices = self.get_xr_matrices(debug=debug)
        xrC, xrP, xrPe = xr_matrices[1:]

        ret_components = []
        for i in range(self.num_components):
            icurve_array = np.array([self.xr_icurve.x, xrC[i,:]])
            jcurve_array = np.array([self.xr.qv, xrP[:,i], xrPe[:,i]]).T
            ccurve = self.xr_ccurves[i]
            ret_components.append(XrComponent(icurve_array, jcurve_array, ccurve))

        return ret_components

    def get_uv_matrices(self, debug=False):
        """
        Get the matrices for the UV data.

        Parameters
        ----------
        debug : bool, optional
            If True, enable debug mode.

        Returns
        -------
        tuple of (np.ndarray, np.ndarray, np.ndarray, np.ndarray)
            The matrices for the UV data.
        """
        if debug:
            from importlib import reload
            import molass.LowRank.LowRankInfo
            reload(molass.LowRank.LowRankInfo)
        from molass.LowRank.LowRankInfo import compute_lowrank_matrices

        uv = self.uv
        return compute_lowrank_matrices(uv.M, self.uv_ccurves, uv.E, self.uv_ranks, debug=debug)

    def get_uv_components(self, debug=False):
        """
        Get the components for the UV data.

        Returns
        -------
        List of UvComponent objects.
        """
        if debug:
            from importlib import reload
            import molass.LowRank.Component
            reload(molass.LowRank.Component)
        from molass.LowRank.Component import UvComponent

        uv_matrices = self.get_uv_matrices(debug=debug)
        uvC, uvP, uvPe = uv_matrices[1:]
        if uvPe is None:
            uvPe = np.zeros_like(uvP)

        ret_components = []
        for i in range(self.num_components):
            uv_elution = np.array([self.uv_icurve.x, uvC[i,:]])
            uv_spectral = np.array([self.uv.wv, uvP[:,i], uvPe[:,i]]).T
            ccurve = self.uv_ccurves[i]
            ret_components.append(UvComponent(uv_elution, uv_spectral, ccurve))

        return ret_components

    def get_pairedranges(self, mapped_curve=None, area_ratio=0.7, concentration_datatype=2, debug=False):
        """
        Get the paired ranges.

        Parameters
        ----------
        mapped_curve : MappedCurve, optional
            If specified, use this mapped curve instead of computing a new one.
        area_ratio : float, optional
            The area ratio for the range computation.
        concentration_datatype : int, optional
            The concentration datatype for the range computation.
        debug : bool, optional
            If True, enable debug mode.

        Returns
        -------
        list of PairedRange
            The list of :class:`~molass.LowRank.PairedRange` objects.
        """
        if self.paired_ranges is None:
            if debug:
                import molass.Reports.ReportRange
                reload(molass.Reports.ReportRange)
            from molass.Reports.ReportRange import make_v1report_ranges_impl
            if mapped_curve is None:
                if self.mapped_curve is None:
                    from molass.Backward.MappedCurve import make_mapped_curve
                    self.mapped_curve = make_mapped_curve(self.ssd, debug=debug)
                mapped_curve = self.mapped_curve
            self.paired_ranges = make_v1report_ranges_impl(self, self.ssd, mapped_curve, area_ratio, concentration_datatype, debug=debug)
        return self.paired_ranges

    def get_proportions(self):
        """
        Get the relative area fractions of the XR components.

        Returns
        -------
        proportions : np.ndarray, shape (n_components,)
            Normalised elution-curve area fraction for each component,
            summing to 1.0.  Values are in the range [0, 1].
            Proportional to the amount (concentration × volume) of each
            species in the SEC peak region.
        """
        n = self.get_num_components()
        props = np.zeros(n)
        for i, c in enumerate(self.get_xr_components()):
            props[i] = c.compute_area()
        return props/np.sum(props)

    def compute_scds(self, debug=False):
        """
        Get the list of SCDs (Score of Concentration Dependence) for the decomposition.

        Returns
        -------
        list of float
            The list of SCD values for each component.
        """
        if debug:
            import molass.Backward.RankEstimator
            reload(molass.Backward.RankEstimator)
        from molass.Backward.RankEstimator import compute_scds_impl
        return compute_scds_impl(self, debug=debug)
    
    def get_cd_color_info(self):
        """
        Get the color information for the concentration dependence.

        Returns
        -------
        peak_top_xes : list of float
            The list of peak top x values for each component.
        scd_colors : list of str
            The list of colors for each component based on their ranks.
        """
        if self.xr_ranks is None:
            import logging
            logging.warning("Decomposition.get_cd_color_info: xr_ranks is None, using default ranks.")
            ranks = [1] * self.num_components
        else:
            ranks = self.xr_ranks

        peak_top_xes = [ccurve.get_peak_top_x() for ccurve in self.xr_ccurves]
        scd_colors = ['green' if rank == 1 else 'red' for rank in ranks]
        return peak_top_xes, scd_colors
    
    def optimize_with_model(self, model_name, rgcurve=None, model_params=None, debug=False):
        """
        Optimize the decomposition with a model.

        Parameters
        ----------
        model_name : str
            The name of the model to use for optimization.

            Supported models:

            - ``SDM``: `Stochastic Dispersive Model <https://biosaxs-dev.github.io/molass-essence/chapters/60/stochastic-theory.html#stochastic-dispersive-model>`_
            - ``EDM``: `Equilibrium Dispersive Model <https://biosaxs-dev.github.io/molass-essence/chapters/60/kinetic-theory.html#equilibrium-dispersive-model>`_

        rgcurve : Curve, optional
            The Rg curve to use for the optimization.

        model_params : dict, optional
            The parameters for the model.

        debug : bool, optional
            If True, enable debug mode.

        Returns
        -------
        result : Decomposition
            A new Decomposition object with optimized components.
        """
        if debug:
            import molass.SEC.ModelFactory
            reload(molass.SEC.ModelFactory)
        from molass.SEC.ModelFactory import create_model
        model = create_model(model_name, debug=debug)
        return model.optimize_decomposition(self, rgcurve=rgcurve, model_params=model_params, debug=debug)
    
    def make_rigorous_initparams(self, baseparams, debug=False):
        """
        Make initial parameters for rigorous optimization.

        Parameters
        ----------
        debug : bool, optional
            If True, enable debug mode.

        Returns
        -------
        np.ndarray
            The initial parameters for rigorous optimization.
        """
        if self.model == 'egh':
            if debug:
                import molass.Rigorous.RigorousEghParams
                reload(molass.Rigorous.RigorousEghParams)
            from molass.Rigorous.RigorousEghParams import make_rigorous_initparams_impl
            return make_rigorous_initparams_impl(self, baseparams, debug=debug)
        elif self.model == 'sdm':
            if debug:
                import molass.Rigorous.RigorousSdmParams
                reload(molass.Rigorous.RigorousSdmParams)
            from molass.Rigorous.RigorousSdmParams import make_rigorous_initparams_impl
            return make_rigorous_initparams_impl(self, baseparams, debug=debug)
        elif self.model == 'edm':
            if debug:
                import molass.Rigorous.RigorousEdmParams
                reload(molass.Rigorous.RigorousEdmParams)
            from molass.Rigorous.RigorousEdmParams import make_rigorous_initparams_impl
            return make_rigorous_initparams_impl(self, baseparams, debug=debug)
        else:
            raise ValueError(f"Decomposition.make_rigorous_initparams: Unsupported model '{self.model}'")

    def optimize_rigorously(self, rgcurve=None, analysis_folder=None, method='BH', niter=20, debug=False):
        """
        Perform a rigorous decomposition.

        Parameters
        ----------
        rgcurve : Curve
            The Rg curve to use for the decomposition.
        analysis_folder : str, optional
            The folder to save analysis results.
        method : str, optional
            The method to use for rigorous optimization. Default is 'BH'.
        niter : int, optional
            The number of iterations for the optimization. Default is 20.
        debug : bool, optional
            If True, enable debug mode.

        Returns
        -------
        result : Decomposition
            A new Decomposition object after rigorous decomposition.
        """
        if debug:
            import molass.Rigorous.RigorousImplement
            reload(molass.Rigorous.RigorousImplement)
        from molass.Rigorous.RigorousImplement import make_rigorous_decomposition_impl

        if rgcurve is None:
            rgcurve = self.ssd.xr.compute_rgcurve()

        return make_rigorous_decomposition_impl(self, rgcurve, analysis_folder=analysis_folder, method=method, niter=niter, debug=debug)
