"""
Testing.HeadlessPeakEditor — headless reproduction of PeakEditor.draw_scores()

Returns the same (init_params, fv, sv, score_names, scores) the GUI displays,
without launching any GUI. Useful for:

  - Programmatic SV comparison across molass_legacy versions
  - Regression tests verifying PeakEditor SV for specific datasets

Quick start::

    from molass.Testing.HeadlessPeakEditor import draw_scores_headless
    from molass_data import SAMPLE1

    result = draw_scores_headless(SAMPLE1)
    print(f"PeakEditor SV = {result['sv']:.2f}")

Copyright (c) 2025-2026, SAXS Team, KEK-PF
"""
import os
import tempfile


def draw_scores_headless(sample_folder, num_peaks=3, use_library_rg=True,
                          poresize=76.0, poresize_bounds=(71.0, 81.0)):
    """Headless equivalent of PeakEditor.draw_scores().

    Replicates the optimizer setup in PeakEditor exactly:
      1. load_data + prepare (get_lrf_source)
      2. compute rg_curve (legacy or library path)
      3. inject rg_curve into dsets
      4. construct_optimizer + compute_init_params
      5. prepare_for_optimization + objective_func(init_params)

    Parameters
    ----------
    sample_folder : str
        Path to raw data folder (e.g. SAMPLE1).
    num_peaks : int
        Number of protein components (matches PeakEditor "Number of Components"
        spinbox). Default: 3.
    use_library_rg : bool
        True (default) → library ssd.get_rg_curve() with w(j)=q·Ĩ weighting
                         (current dev path, recommended).
        False           → legacy RgCurve starting at first-peak frame
                          (matches installed 1.6.5 behavior).
    poresize : float
        Column pore size in Å. Default: 76.0 (Superdex 75).
    poresize_bounds : tuple
        (lower, upper) bounds for pore size. Default: (71.0, 81.0).

    Returns
    -------
    dict with keys:
        ``molass_legacy_path`` (str), ``n_params`` (int),
        ``init_params`` (np.ndarray), ``fv`` (float), ``sv`` (float),
        ``score_names`` (list[str]), ``scores`` (np.ndarray)

    Example
    -------
    >>> from molass.Testing.HeadlessPeakEditor import draw_scores_headless
    >>> from molass_data import SAMPLE1
    >>> result = draw_scores_headless(SAMPLE1)
    >>> print(f"PeakEditor SV = {result['sv']:.2f}")
    """
    import molass_legacy as ml_pkg
    import numpy as np

    from molass_legacy.Batch.LiteBatch import LiteBatch
    from molass_legacy.Optimizer.FuncImporter import get_objective_function_info
    from molass_legacy.Optimizer.FvScoreConverter import convert_score
    from molass_legacy._MOLASS.SerialSettings import set_setting

    ml_path = ml_pkg.__file__

    lb = LiteBatch()

    # Set settings BEFORE get_lrf_source so EghAdvansedParams is chosen when
    # construct_egh_params_type is called inside G0346.__init__.
    set_setting('uv_basemodel', 1)
    set_setting('poresize', poresize)
    set_setting('poresize_bounds', poresize_bounds)

    # load_data + prepare + get_curve_xy + get_modeled_peaks (full GUI path)
    lb.get_lrf_source(in_folder=sample_folder)

    # Truncate detected peaks to exactly num_peaks, matching the GUI spinbox.
    pps = lb.peak_params_set
    if len(pps[1]) > num_peaks:
        from molass_legacy.Peaks.PeakParamsSet import PeakParamsSet
        lb.peak_params_set = PeakParamsSet(pps[0][:num_peaks], pps[1][:num_peaks],
                                           pps[2], pps[3])
    lb.exact_num_peaks = len(lb.peak_params_set[1])

    # Build rg_curve: library (recommended, w(j)=q·Ĩ) or legacy (1.6.5-compatible)
    if use_library_rg:
        # Library path: ssd.get_rg_curve() with combined w(j)=q·Ĩ weighting in
        # GuinierDeviation (dev default, starts at frame 0, suppresses buffer noise)
        from molass.Bridge.SdAdapter import make_ssd_from_corrected_sd
        from molass.Bridge.LegacyRgCurve import LegacyRgCurve
        from molass_legacy.Optimizer.OptDataSets import OptDataSets

        ssd = make_ssd_from_corrected_sd(lb.corrected_sd)
        library_rgcurve = ssd.get_rg_curve()

        D, E, qv, xr_curve_sd = lb.corrected_sd.get_xr_data_separate_ly()
        uv_ret = lb.corrected_sd.get_uv_data_separate_ly()
        U, uv_curve_sd = uv_ret[0], uv_ret[-1]
        xr_curve_sd = lb.sd.get_xr_data_separate_ly()[3]
        real_rg_curve = LegacyRgCurve(xr_curve_sd, library_rgcurve)
        raw_tuple = ((xr_curve_sd, D), real_rg_curve, (uv_curve_sd, U))
        real_dsets = OptDataSets(lb.sd, lb.corrected_sd, dsets=raw_tuple, E=E)
    else:
        # Legacy path: OptDataSets(compute_rg=True), starts at first-peak frame
        from molass_legacy.Optimizer.OptDataSets import OptDataSets
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_opt = os.path.join(tmp_dir, 'optimized')
            os.makedirs(tmp_opt, exist_ok=True)
            set_setting('analysis_folder', tmp_dir)
            set_setting('optimizer_folder', tmp_opt)
            real_dsets = OptDataSets(lb.sd, lb.corrected_sd,
                                     compute_rg=True, possibly_relocated=False)

    # Replicate get_init_estimate() with real rg_curve injected
    lb.func_info = get_objective_function_info(lb.logger, default_func_code='G0346')
    lb.func_dict = lb.func_info.func_dict
    lb.key_list = lb.func_info.key_list
    lb.dsets = real_dsets
    set_setting('uv_basemodel', 1)
    set_setting('poresize', poresize)
    set_setting('poresize_bounds', poresize_bounds)
    lb.construct_optimizer()
    lb.optimizer.rg_curve = real_dsets[1]
    init_params = lb.compute_init_params()

    lb.optimizer.prepare_for_optimization(init_params)
    full = lb.optimizer.objective_func(init_params, return_full=True)
    fv = float(full[0])
    score_list = np.array([float(s) for s in full[1]])
    sv = float(convert_score(fv))
    score_names = lb.optimizer.get_score_names()

    return {
        "molass_legacy_path": ml_path,
        "n_params": len(init_params),
        "init_params": np.array(init_params),
        "fv": fv,
        "sv": sv,
        "score_names": score_names,
        "scores": score_list,
    }
