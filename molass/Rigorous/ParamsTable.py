"""
Rigorous.ParamsTable.py

Model-agnostic "Show Parameters" data extractor.

Promoted from molass-researcher/experiments/34_ssd_rigorous_gui/34k_show_parameters_design.ipynb,
where it was validated against EGH, SDM, CEDM, LKM and GRM (SAMPLE1). Replaces the legacy
per-model ``*ParamsSheet`` classes' hand-built row/col grids with one shared extractor plus
one small per-model namer for the trailing ``model_colparams`` tuple.

This module only builds the data (a tidy ``pandas.DataFrame``); rendering (notebook display,
``tksheet.Sheet``, etc.) is left to the caller.
"""
import numpy as np
import pandas as pd

_EGH_XR_LABELS = ["h", "mu (tR)", "sigma", "tau"]


def common_param_rows(xr_params, xr_baseparams, rgs, mapping, uv_params, uv_baseparams,
                       mappable_range, xr_labels=None):
    """Build the model-agnostic rows: xr/rg, xr baseline, uv, uv baseline, mapping, range.

    Everything except ``model_colparams`` (see the per-model ``*_colparam_rows`` functions)
    is identical across EGH/SDM/EDM/CEDM/LKM/GRM.

    Parameters
    ----------
    xr_params, xr_baseparams, rgs, mapping, uv_params, uv_baseparams, mappable_range :
        The first seven elements of ``optimizer.split_params_simple(params)``.
    xr_labels : list of str, optional
        Column names for ``xr_params``. Defaults to EGH's ``[h, mu (tR), sigma, tau]``
        truncated to the actual column count -- pass explicitly for models whose
        per-component params mean something else (e.g. CEDM's ``[a, b, c_inj]``).

    Returns
    -------
    list of dict
        Rows with keys ``section``, ``label``, ``component``, ``value``.
    """
    rows = []
    xr_params = np.asarray(xr_params)
    if xr_params.ndim == 1:
        # SDM/EDM/CEDM/LKM/GRM: one scale per component (flat), not an EGH-style
        # (component, param) matrix -- np.atleast_2d would misread this as a
        # single row instead of n rows, silently dropping components 2..n.
        xr_params = xr_params.reshape(-1, 1)
    n = xr_params.shape[0]
    if xr_labels is None:
        xr_labels = _EGH_XR_LABELS[:xr_params.shape[1]]

    for i in range(n):
        for j, label in enumerate(xr_labels):
            rows.append({"section": "xr", "label": label, "component": i + 1, "value": xr_params[i, j]})
        rows.append({"section": "xr", "label": "rg", "component": i + 1, "value": rgs[i]})

    for j, label in enumerate(["slope", "intercept", "fouling"][:len(xr_baseparams)]):
        rows.append({"section": "xr_baseline", "label": label, "component": None, "value": xr_baseparams[j]})

    uv_params = np.atleast_1d(uv_params)
    for i, v in enumerate(uv_params):
        rows.append({"section": "uv", "label": "h", "component": i + 1, "value": v})

    uv_bp_labels = ["L", "x0", "k", "b", "s1", "s2", "diff_ratio", "fouling"][:len(uv_baseparams)]
    for j, label in enumerate(uv_bp_labels):
        rows.append({"section": "uv_baseline", "label": label, "component": None, "value": uv_baseparams[j]})

    for j, label in enumerate(["slope", "intercept"]):
        rows.append({"section": "mapping", "label": label, "component": None, "value": mapping[j]})

    for j, label in enumerate(["from", "to"]):
        rows.append({"section": "mappable_range", "label": label, "component": None, "value": mappable_range[j]})

    return rows


def egh_colparam_rows(colparams):
    """Namer for plain EGH's ``model_colparams`` -- a 6-element SEC-column tuple.

    Confirmed via a live run: EGH's ``model_colparams`` is NOT None even though the
    elution model itself is column-free; ``upgrade()`` still estimates SEC column
    params (``Npc, rp, tI, t0, P, m``) alongside the free EGH shape params.
    """
    if colparams is None:
        return []
    names = ["Npc", "rp (pore size)", "tI", "t0", "P", "m"]
    if len(colparams) != len(names):
        names = [f"param_{i}" for i in range(len(colparams))]
    return [{"section": "column", "label": name, "component": None, "value": v}
            for name, v in zip(names, colparams)]


def sdm_colparam_rows(colparams):
    """Namer for SDM's ``model_colparams``: ``[N, K, t0, rp, N0, tI]`` (+ optional ``k``)."""
    N, K, t0, rp, N0, tI = colparams[:6]
    T = K / N
    names = ["N", "K (=N*T)", "t0", "rp (pore size)", "N0", "tI", "T (derived)"]
    values = [N, K, t0, rp, N0, tI, T]
    rows = [{"section": "column", "label": n, "component": None, "value": v}
            for n, v in zip(names, values)]
    # Legacy SdmParamsSheet.py only reads colparams[:6] -- flag any extra trailing
    # value instead of silently dropping it like the legacy sheet does.
    if len(colparams) > 6:
        for i, v in enumerate(colparams[6:], start=6):
            rows.append({"section": "column", "label": f"param_{i} (unidentified)",
                         "component": None, "value": v})
    return rows


def cedm_colparam_rows(colparams):
    """Namer for CEDM's ``model_colparams``: shared ``[t0_sh, u_sh, e_sh, Dz_sh]``."""
    names = ["t0_sh", "u_sh", "e_sh", "Dz_sh"]
    return [{"section": "column", "label": n, "component": None, "value": v}
            for n, v in zip(names, colparams)]


def lkm_colparam_rows(colparams, n_components):
    """Namer for LKM's ``model_colparams``.

    Current source (``LkmParams.py``, not the stale legacy sheet docstring):
    ``num_col_params = 3 + 2*nc``, ``nc = n_components - 1``, layout =
    ``[Pe, t0, c_inj, R_0, k_MT_0, ..., R_{nc-1}, k_MT_{nc-1}]``.
    """
    nc = n_components - 1
    rows = [
        {"section": "column", "label": "Pe", "component": None, "value": colparams[0]},
        {"section": "column", "label": "t0", "component": None, "value": colparams[1]},
        {"section": "column", "label": "c_inj", "component": None, "value": colparams[2]},
    ]
    for k in range(nc):
        R_k, k_MT_k = colparams[3 + 2 * k], colparams[4 + 2 * k]
        rows.append({"section": "column", "label": "R", "component": k + 1, "value": R_k})
        rows.append({"section": "column", "label": "k_MT", "component": k + 1, "value": k_MT_k})
    return rows


def grm_colparam_rows(colparams, n_components):
    """Namer for GRM's ``model_colparams``.

    Current source (``GrmParams.py``, not the stale legacy sheet docstring):
    ``num_col_params = 5 + 2*nc``, ``nc = n_components - 1``, layout =
    ``[Pe, t0, R_p, D_eff, c_inj, R_0, k_ext_0, ..., R_{nc-1}, k_ext_{nc-1}]``.
    """
    nc = n_components - 1
    names = ["Pe", "t0", "R_p", "D_eff", "c_inj"]
    rows = [{"section": "column", "label": n, "component": None, "value": v}
            for n, v in zip(names, colparams[:5])]
    for k in range(nc):
        R_k, k_ext_k = colparams[5 + 2 * k], colparams[6 + 2 * k]
        rows.append({"section": "column", "label": "R", "component": k + 1, "value": R_k})
        rows.append({"section": "column", "label": "k_ext", "component": k + 1, "value": k_ext_k})
    return rows


# Per-model xr_labels override -- only needed where the default (EGH labels truncated
# to the actual column count) would be wrong. SDM/LKM/GRM's single "scale" column
# correctly defaults to ["h"], so they're omitted here.
_XR_LABELS_BY_MODEL = {
    "EDM": ["a", "b", "c_inj"],
    "CEDM": ["a", "b", "c_inj"],
}


def build_params_table(optimizer, params):
    """Build the full "Show Parameters" table for any supported rigorous model.

    Dispatches on ``optimizer.get_model_name()`` to pick the right ``xr_labels`` and
    ``model_colparams`` namer, then combines :func:`common_param_rows` with the
    model-specific column rows.

    Parameters
    ----------
    optimizer :
        A rigorous optimizer, e.g. from ``Score.optimizer`` (see :meth:`Decomposition.score`).
    params : array-like
        The parameter vector to display, e.g. ``Score.init_params`` or ``RunInfo.best_params``.

    Returns
    -------
    pandas.DataFrame
        Columns: ``section``, ``label``, ``component``, ``value``.
    """
    parts = optimizer.split_params_simple(params)
    (xr_params, xr_baseparams, rgs, mapping, uv_params, uv_baseparams,
     mappable_range, colparams) = parts

    model_name = optimizer.get_model_name()
    xr_labels = _XR_LABELS_BY_MODEL.get(model_name)
    rows = common_param_rows(xr_params, xr_baseparams, rgs, mapping, uv_params, uv_baseparams,
                              mappable_range, xr_labels=xr_labels)

    if model_name == 'EGH':
        rows += egh_colparam_rows(colparams)
    elif model_name == 'SDM':
        rows += sdm_colparam_rows(colparams)
    elif model_name in ('EDM', 'CEDM'):
        rows += cedm_colparam_rows(colparams)
    elif model_name == 'LKM':
        rows += lkm_colparam_rows(colparams, optimizer.n_components)
    elif model_name == 'GRM':
        rows += grm_colparam_rows(colparams, optimizer.n_components)
    else:
        raise ValueError(f"Unsupported model_name for build_params_table: {model_name}")

    return pd.DataFrame(rows)
