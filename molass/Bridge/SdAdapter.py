"""
Bridge.SdAdapter.py

Converts a legacy SerialData (sd) into a library SecSaxsData (ssd).
This is an incremental step on the data-object consolidation track defined in
Rule 13 of copilot-guidelines.md (target: molass-legacy GUI → molass-library).

Only the corrected-sd → ssd direction is implemented here.  The reverse
(ssd → sd) is not needed yet.
"""
import numpy as np


def make_ssd_from_corrected_sd(corrected_sd):
    """Build a library SecSaxsData from a baseline-corrected legacy SerialData.

    The input *must* be a corrected (baseline-subtracted) sd, i.e.
    ``corrected_sd.baseline_corrected is True``.  The returned ssd has its
    ``trimmed`` and ``corrected`` flags set so that ``quick_decomposition()``
    can be called directly without a redundant ``corrected_copy()`` step.

    Parameters
    ----------
    corrected_sd : molass_legacy.SerialAnalyzer.SerialData.SerialData
        A trimmed, baseline-corrected legacy data object.

    Returns
    -------
    molass.DataObjects.SecSaxsData.SecSaxsData
        Library data object ready for ``quick_decomposition()``.
    """
    from molass.DataObjects.XrData import XrData
    from molass.DataObjects.UvData import UvData
    from molass.DataObjects.SecSaxsData import SecSaxsData

    # --- XR side ---
    # intensity_array shape: (n_frames, n_q, 3)  columns: (q, I, E)
    ia = corrected_sd.intensity_array
    xrM = ia[:, :, 1].T          # (n_q, n_frames) — intensity
    xrE = ia[:, :, 2].T          # (n_q, n_frames) — error
    qv  = corrected_sd.qvector   # (n_q,) — q values
    jv_xr = np.arange(xrM.shape[1], dtype=float)

    # --- UV side ---
    # absorbance.data shape: (n_wl, n_frames) — already wavelength-trimmed by Absorbance.__init__
    absorbance = corrected_sd.absorbance
    uvM = absorbance.data          # (n_wl, n_frames)
    wv  = absorbance.wl_vector     # (n_wl,) — wavelengths in nm
    jv_uv = np.arange(uvM.shape[1], dtype=float)

    xr_data = XrData(xrM, qv, jv_xr, xrE)
    uv_data = UvData(uvM, wv,  jv_uv)

    ssd = SecSaxsData(object_list=[xr_data, uv_data], trimmed=True)
    # Mark as corrected so optimize_rigorously() does not emit the Pattern A warning
    # (molass-library#164) if this ssd is later passed to the optimizer path.
    ssd.corrected = True

    return ssd


def decomposition_from_optimizer_params(fullopt, params, base_decomp):
    """Build a library Decomposition from a legacy optimizer + flat params vector.

    This is the model-dependent update path used by
    ``JobStateCanvas._update_decomposition_to_current()``.  It reuses the
    existing ``ComponentUtils.get_xr_ccurves`` dispatch table, which already
    handles all five models (EGH, SDM, EDM/CEDM, LKM).

    Parameters
    ----------
    fullopt : molass_legacy.Optimizer.BasicOptimizer.BasicOptimizer
        The live legacy optimizer instance.  Used only for
        ``split_params_simple(params)`` and ``get_model_name()`` — no heavy
        computation is triggered.
    params : array-like
        Flat optimizer parameter vector at the desired snapshot
        (e.g. ``demo_info[1][curr_index]``).
    base_decomp : molass.LowRank.Decomposition.Decomposition
        The base decomposition that owns the ``ssd``.  Its ``ssd`` is reused
        as the data container; only the component curves are replaced.

    Returns
    -------
    molass.LowRank.Decomposition.Decomposition
        A new Decomposition whose XR/UV component curves reflect ``params``.
    """
    import numpy as np
    from molass.Rigorous.ComponentUtils import get_xr_ccurves
    from molass.SEC.Models.UvComponentCurve import UvComponentCurve
    from molass.Mapping.Mapping import Mapping

    ssd = base_decomp.ssd
    xr_icurve = ssd.xr.get_icurve()
    uv_icurve = ssd.uv.get_icurve() if ssd.has_uv() else None

    separated_params = fullopt.split_params_simple(params)
    xr_ccurves = get_xr_ccurves(fullopt, xr_icurve, separated_params)

    a, b = separated_params[3]
    mapping = Mapping(a, b)
    uv_params = separated_params[4]
    x = uv_icurve.x if uv_icurve is not None else xr_icurve.x

    uv_ccurves = []
    for xr_ccurve, scale in zip(xr_ccurves, uv_params):
        xr_h = xr_ccurve.get_scale_param()
        uv_ccurves.append(UvComponentCurve(x, mapping, xr_ccurve, scale / xr_h))

    optimizer_rgs = np.asarray(separated_params[2], dtype=float)
    return base_decomp.copy_with_new_components(xr_ccurves, uv_ccurves,
                                                 optimizer_rgs=optimizer_rgs)


def make_ssd_from_dsets(dsets, sd):
    """Build a library SecSaxsData from a legacy OptDataSets + trimmed SerialData.

    Used by ``JobStateCanvas`` in the legacy GUI path, where only ``dsets``
    (already corrected) and the trimmed ``sd`` (for q-values and wavelengths)
    are available — ``corrected_sd`` is not stored in that path.

    Parameters
    ----------
    dsets : molass_legacy.Optimizer.OptDataSets.OptDataSets
        The prepared optimizer dataset.  Iterated as
        ``((xr_curve, D), rg_curve, (uv_curve, U))``.
    sd : molass_legacy.SerialAnalyzer.SerialData.SerialData
        Trimmed (uncorrected) legacy data object — used only for ``qvector``
        and ``absorbance.wl_vector``.

    Returns
    -------
    molass.DataObjects.SecSaxsData.SecSaxsData
        Library data object ready for ``quick_decomposition()``.
    """
    from molass.DataObjects.XrData import XrData
    from molass.DataObjects.UvData import UvData
    from molass.DataObjects.SecSaxsData import SecSaxsData

    (xr_curve, D), _rg_curve, (uv_curve, U) = dsets

    # D shape: (n_q, n_frames) — already corrected (same as ssd.xr.M)
    qv    = sd.qvector
    jv_xr = xr_curve.x

    # U shape: (n_wl, n_frames); wavelengths from the Absorbance object
    wv    = sd.absorbance.wl_vector
    jv_uv = uv_curve.x

    # Error matrix: column 2 of intensity_array (same shape as D, not baseline-corrected
    # but the per-measurement uncertainty is independent of baseline correction).
    xrE = sd.intensity_array[:, :, 2].T  # (n_q, n_frames)

    xr_data = XrData(D, qv, jv_xr, xrE)
    uv_data = UvData(U, wv, jv_uv)

    ssd = SecSaxsData(object_list=[xr_data, uv_data], trimmed=True)
    ssd.corrected = True

    return ssd
