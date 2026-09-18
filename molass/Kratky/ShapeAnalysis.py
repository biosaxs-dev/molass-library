"""
Kratky.ShapeAnalysis

Qualitative + quantitative shape-match diagnostics for decomposed XR
components, using dimensionless Kratky-plot analysis.

Design rationale (see molass-researcher/experiments/41_smoothing_kratky_plot/
41a-41e for the full investigation this is based on):

- The rigorous optimizer's ``Kratky_smoothness`` score (raw point-to-point
  roughness) was found to be unreliable as a decomposition-quality signal --
  it can actively reward objectively worse decompositions (merged/under-fit
  components look "smoother" purely because merging improves per-point SNR).
- Peak-position deviation from the theoretical qRg=sqrt(3) (Guinier's law)
  is a genuinely useful, non-gameable *shape* diagnostic, but a literal
  fitted-shape inversion (a specific ellipsoid eccentricity or cylinder
  aspect ratio) is misleadingly precise: peak position alone cannot
  disambiguate shape family (an ellipsoid and a cylinder can produce nearly
  identical peaks), and the whole premise assumes the component is a
  genuinely well-resolved single species, which a distorted/wrong
  decomposition can silently violate.
- The approach implemented here instead computes a **relative match score**
  against a small, fixed library of reference shapes, displayed as a
  components x shapes score matrix (see ``plot_shape_analysis``). Scores are
  a heuristic similarity measure, NOT a rigorous statistical likelihood, and
  should always be read together with an independent decomposition-quality
  signal (``Decomposition.get_lrf_residual()``, and the ``peak_spread``
  attached to this module's result) -- shape category / match score and
  bulk fit quality were found to catch *different* kinds of decomposition
  problems, not the same one.
"""
import numpy as np
from scipy.signal import savgol_filter

from molass.Kratky.ShapeLibrary import get_model_shapes

QRG_PEAK_SEARCH_WINDOW = (0.5, 5.0)
QRG_MATCH_WINDOW = (0.5, 5.0)
GLOBULAR_PEAK_QRG = np.sqrt(3)



def _savgol_smooth(y, window=11, polyorder=3):
    window = min(window, len(y) - (1 - len(y) % 2))
    if window % 2 == 0:
        window -= 1
    window = max(window, polyorder + 2 if (polyorder + 2) % 2 else polyorder + 3)
    return savgol_filter(y, window_length=window, polyorder=polyorder)


def kratky_peak_qrg(qv, pv, rg, iz, qrg_search_window=QRG_PEAK_SEARCH_WINDOW):
    """Locate a component's dimensionless Kratky peak, restricted to the
    physically expected globular-peak window.

    A naive whole-curve argmax can be fooled by a genuine or spurious upturn
    at high qRg; restricting the search avoids that (see molass-researcher
    experiment 41b/41c).

    Parameters
    ----------
    qv : ndarray
        q-values (Å⁻¹).
    pv : ndarray
        Component's scattering profile P(q) (one column of ``get_xr_matrices()``'s P).
    rg : float
        Component's radius of gyration (Å).
    iz : float
        Component's forward scattering I(0).
    qrg_search_window : tuple of float, optional
        (min, max) qRg range to search for the peak. Default (0.5, 5.0).

    Returns
    -------
    float or None
        The peak's qRg location, or None if no interior peak was found
        (curve is still rising at the window's right edge -- "no clear peak").
    """
    qrg = qv * rg
    kratky_y = qrg**2 * pv / iz
    smoothed = _savgol_smooth(kratky_y, window=11, polyorder=3)
    mask = (qrg >= qrg_search_window[0]) & (qrg <= qrg_search_window[1])
    if not mask.any():
        return None
    idx = np.where(mask)[0]
    local_peak_idx = idx[np.argmax(smoothed[mask])]
    if local_peak_idx == idx[-1]:
        return None  # no decay observed -- treat as "no clear peak"
    return float(qrg[local_peak_idx])


def classify_shape_category(peak_qrg):
    """Bucket a peak qRg into a coarse, honestly-labeled shape category.

    Boundaries are heuristic, calibrated from the exact-form-factor
    simulation in molass-researcher experiment 41d (sphere=1.605,
    near-spherical ellipsoid=1.625, oblate ellipsoid=1.765, prolate
    ellipsoid eps=3 -> 2.186, eps=10 -> 6.677). Not a validated,
    precisely-fitted classifier -- see this module's docstring.

    Parameters
    ----------
    peak_qrg : float or None
        Output of :func:`kratky_peak_qrg`.

    Returns
    -------
    str
        One of: "anomalously low (below any simulated compact shape -- check
        decomposition)", "compact / globular", "moderately anisotropic",
        "elongated / rod-like", "highly elongated or flexible/disordered
        (no clear peak)".
    """
    if peak_qrg is None:
        return "highly elongated or flexible/disordered (no clear peak)"
    if peak_qrg < 1.55:
        return "anomalously low (below any simulated compact shape -- check decomposition)"
    if peak_qrg <= 1.9:
        return "compact / globular"
    if peak_qrg <= 2.8:
        return "moderately anisotropic"
    if peak_qrg <= 6.0:
        return "elongated / rod-like"
    return "highly elongated or flexible/disordered"


def _match_score(component_qrg, component_ky, model_Rg, model_P_fn,
                  qrg_window=QRG_MATCH_WINDOW):
    """Heuristic similarity (NOT a statistical likelihood): exp(-normalized RMSE)
    between the component's own Kratky curve and a reference shape's curve,
    both evaluated on the component's own qRg grid within qrg_window."""
    mask = (component_qrg >= qrg_window[0]) & (component_qrg <= qrg_window[1])
    if mask.sum() < 5:
        return np.nan
    qrg_m = component_qrg[mask]
    ky_m = component_ky[mask]
    qs = qrg_m / model_Rg
    ref_y = qrg_m**2 * model_P_fn(qs)
    rmse = np.sqrt(np.mean((ky_m - ref_y)**2))
    scale = np.std(ky_m) if np.std(ky_m) > 1e-6 else 1.0
    return float(np.exp(-(rmse/scale)))


class ShapeAnalysisResult:
    """Result of :func:`compute_shape_match_scores`.

    Attributes
    ----------
    shape_names : list of str
        Column labels for ``score_matrix`` (the fixed reference-shape library).
    component_labels : list of str
        Row labels, e.g. ``"component-1 (Rg=35.9)"``.
    score_matrix : ndarray, shape (n_components, n_shapes)
        Row-normalized heuristic match scores (each row sums to ~1, or is
        all-NaN if that component had no usable Rg/peak data).
    categories : list of str
        Discrete shape-category label per component (see
        :func:`classify_shape_category`).
    peak_qrgs : list of float or None
        Peak qRg per component (None = no clear peak).
    peak_spread : float or None
        Std of the valid ``peak_qrgs`` across components -- a
        cross-component consistency signal distinct from any single
        component's category (molass-researcher experiment 41b/41c found
        this catches decomposition problems that a bulk LRF residual can
        miss, and vice versa).
    """

    def __init__(self, shape_names, component_labels, score_matrix, categories,
                 peak_qrgs, peak_spread):
        self.shape_names = shape_names
        self.component_labels = component_labels
        self.score_matrix = score_matrix
        self.categories = categories
        self.peak_qrgs = peak_qrgs
        self.peak_spread = peak_spread

    def __repr__(self):
        lines = [f"ShapeAnalysisResult({len(self.component_labels)} components, "
                 f"{len(self.shape_names)} reference shapes, peak_spread={self.peak_spread})"]
        for label, cat, peak in zip(self.component_labels, self.categories, self.peak_qrgs):
            peak_str = f"{peak:.3f}" if peak is not None else "none"
            lines.append(f"  {label}: peak_qRg={peak_str}  category={cat}")
        return "\n".join(lines)


def compute_shape_match_scores(qv, P, sg_list):
    """Compute the components x reference-shapes match-score matrix.

    Parameters
    ----------
    qv : ndarray
        q-values (Å⁻¹) -- typically ``decomp.xr.qv``.
    P : ndarray, shape (n_q, n_components)
        Scattering profiles -- typically ``decomp.get_xr_matrices()[2]``.
    sg_list : list
        Per-component Guinier objects (with ``.Rg``/``.Iz``) -- typically
        ``[c.get_guinier_object() for c in decomp.get_xr_components()]``.

    Returns
    -------
    ShapeAnalysisResult

    Examples
    --------
    ::

        from molass.Kratky.ShapeAnalysis import compute_shape_match_scores
        qv = decomp.xr.qv
        _, _, P = decomp.get_xr_matrices()[0:3]
        sg_list = [c.get_guinier_object() for c in decomp.get_xr_components()]
        result = compute_shape_match_scores(qv, P, sg_list)
        print(result)
    """
    model_shapes = get_model_shapes()
    shape_names = [spec.name for spec in model_shapes]

    component_labels = []
    score_rows = []
    categories = []
    peak_qrgs = []

    for k, sg in enumerate(sg_list):
        rg, iz = sg.Rg, sg.Iz
        if rg is None or (isinstance(rg, float) and np.isnan(rg)):
            component_labels.append(f"component-{k+1} (Rg=unavailable)")
            score_rows.append(np.full(len(model_shapes), np.nan))
            categories.append("Rg unavailable")
            peak_qrgs.append(None)
            continue

        qrg = qv * rg
        ky = qrg**2 * P[:, k] / iz
        peak = kratky_peak_qrg(qv, P[:, k], rg, iz)

        scores = np.array([_match_score(qrg, ky, spec.Rg, spec.P_fn)
                            for spec in model_shapes])
        row_sum = np.nansum(scores)
        scores_norm = scores / row_sum if row_sum > 0 else scores

        component_labels.append(f"component-{k+1} (Rg={rg:.1f})")
        score_rows.append(scores_norm)
        categories.append(classify_shape_category(peak))
        peak_qrgs.append(peak)

    valid_peaks = np.array([p for p in peak_qrgs if p is not None])
    peak_spread = float(np.std(valid_peaks)) if len(valid_peaks) > 1 else None

    return ShapeAnalysisResult(
        shape_names=shape_names,
        component_labels=component_labels,
        score_matrix=np.array(score_rows),
        categories=categories,
        peak_qrgs=peak_qrgs,
        peak_spread=peak_spread,
    )


def plot_shape_analysis(result, ax=None, title="Component x model-shape match score",
                         show_shape_key=True):
    """Render a :class:`ShapeAnalysisResult` as a components x shapes heatmap.

    Parameters
    ----------
    result : ShapeAnalysisResult
        Output of :func:`compute_shape_match_scores`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw the heatmap into. If None, a new figure is created (in
        that case, ``show_shape_key`` also controls whether a fixed 3D shape
        key is added as a top row -- see :mod:`molass.Kratky.ShapeKey`).
        If an existing ``ax`` is passed (embedding into a caller-controlled
        layout), the shape key is never added; the caller owns the layout.
    title : str, optional
    show_shape_key : bool, optional
        When creating its own figure, prepend a fixed reference-shape key
        (sphere / mild ellipsoid / elongated ellipsoid / flexible chain) as a
        top row, for at-a-glance visual recognition alongside the heatmap's
        text labels. Default True. The key never changes per analysis --
        rendered once per process and reused (see
        :func:`molass.Kratky.ShapeKey.get_shape_key_image`).

    Returns
    -------
    PlotResult
        Has ``.fig``, ``.axes`` (the heatmap Axes specifically, even when the
        shape key row is also present, for consistency with other molass
        plot functions).

    Examples
    --------
    ::

        result = decomp.get_shape_analysis()
        plot_result = plot_shape_analysis(result)
        plot_result.fig.show()
    """
    import matplotlib.pyplot as plt
    from molass.PlotUtils.PlotResult import PlotResult

    n_shapes = len(result.shape_names)
    matrix = result.score_matrix
    vmax = np.nanmax(matrix) if np.isfinite(matrix).any() else 1.0

    own_fig = ax is None
    if own_fig:
        height = 0.45*len(result.component_labels) + 1.5
        if show_shape_key:
            from molass.Kratky.ShapeKey import get_shape_key_image
            key_image = get_shape_key_image()
            key_height = 1.3  # fixed, independent of the cached image's raw pixel size
            cbar_width = 0.35  # dedicated colorbar column -- kept OUT of the n_shapes
                               # equal-width columns so the icon row and heatmap span
                               # exactly the same width and align 1:1, column by column
            fig = plt.figure(figsize=(8 + cbar_width, height + key_height))
            gs = fig.add_gridspec(2, n_shapes + 1,
                                   height_ratios=[key_height, height],
                                   width_ratios=[1]*n_shapes + [cbar_width])

            key_ax = fig.add_subplot(gs[0, :n_shapes])
            key_ax.imshow(key_image, aspect="auto")  # stretch to fill the row -- a fixed
            key_ax.axis("off")                       # icon strip, not a precise pixel-ratio figure

            ax = fig.add_subplot(gs[1, :n_shapes])
            im = ax.imshow(matrix, cmap="viridis", aspect="auto", vmin=0, vmax=vmax)

            cax = fig.add_subplot(gs[1, n_shapes])
            fig.colorbar(im, cax=cax, label="relative match score (row-normalized)")
        else:
            fig, ax = plt.subplots(figsize=(8, height))
            im = ax.imshow(matrix, cmap="viridis", aspect="auto", vmin=0, vmax=vmax)
            fig.colorbar(im, ax=ax, label="relative match score (row-normalized)")
    else:
        fig = ax.figure
        im = ax.imshow(matrix, cmap="viridis", aspect="auto", vmin=0, vmax=vmax)
        fig.colorbar(im, ax=ax, label="relative match score (row-normalized)")

    ax.set_xticks(range(n_shapes))
    ax.set_xticklabels(result.shape_names, rotation=30, ha="right")
    ax.set_yticks(range(len(result.component_labels)))
    ax.set_yticklabels(result.component_labels, fontsize=8)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            val = matrix[i, j]
            if np.isfinite(val):
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        color="white" if val < 0.5*vmax else "black", fontsize=7)
    ax.set_title(title)

    if own_fig and not show_shape_key:
        fig.tight_layout()
    elif own_fig and show_shape_key:
        fig.subplots_adjust(left=0.22, right=0.85, bottom=0.28, top=0.95, hspace=0.35)

    return PlotResult(fig, ax, result=result)


