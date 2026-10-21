"""
Kratky.ShapeMatch

Qualitative + quantitative Kratky shape-match diagnostics for decomposed XR
components, using dimensionless Kratky-plot analysis (shown in the GUI as
"Kratky Shape Match").

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
  components x shapes score matrix (see ``plot_shape_match``). Scores are
  a heuristic similarity measure, NOT a rigorous statistical likelihood, and
  should always be read together with an independent decomposition-quality
  signal (``Decomposition.get_lrf_residual()``, and the ``peak_spread``
  attached to this module's result) -- shape category / match score and
  bulk fit quality were found to catch *different* kinds of decomposition
  problems, not the same one.
"""
import numpy as np
from scipy.signal import savgol_filter, savgol_coeffs

from molass.Kratky.ShapeLibrary import get_model_shapes, get_shape_color

QRG_PEAK_SEARCH_WINDOW = (0.5, 5.0)
# The match window reaches beyond the main peak so that a second hump (e.g. a dumbbell of lobes, component 1 of
# Y17AH20N at qRg ~8.5) is scored; it was (0.5, 5.0) before molass-researcher experiment 49o. Noise grows ~5x
# towards high qRg, so going much beyond 7.5 would need a noise-weighted score.
QRG_MATCH_WINDOW = (0.5, 7.5)
GLOBULAR_PEAK_QRG = np.sqrt(3)
CHAIN_GATE_FACTOR = 0.05  # score multiplier for the Gaussian chain when the component has a clear peak
TWO_LOBE_GATE_FACTOR = 0.05  # score multiplier for the two-lobe entries when the component shows no second hump
OVERLAY_QRG_MAX = 10.0  # upper end of the qRg range shown by plot_kratky_overlay


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


def has_clear_kratky_peak(qrg, ky, search=(0.5, 11.0), min_decay=0.08, nsigma=3.0):
    """Whether a Kratky curve has a clear interior peak.

    "Clear" means the smoothed maximum is not at the search-window edge and the
    curve falls after it by at least ``min_decay`` (relative) AND by more than
    ``nsigma`` times the local noise, so neither a monotonic/plateauing curve
    nor a noisy plateau counts as peaked. Used to exclude the Gaussian chain
    (which has no peak) from the candidates of a peaked component (see
    molass-researcher experiment 49b).

    Parameters
    ----------
    qrg : ndarray
        Dimensionless q*Rg values.
    ky : ndarray
        Dimensionless Kratky values (qRg)^2 P(q)/I(0).
    search : tuple of float, optional
        (min, max) qRg range in which the peak is searched.
    min_decay : float, optional
    nsigma : float, optional

    Returns
    -------
    bool
    """
    n = len(ky)
    w = min(21, n - (1 - n % 2))
    if w < 5:
        return False
    smoothed = savgol_filter(ky, w, 3)
    resid = ky - smoothed
    idx = np.where((qrg >= search[0]) & (qrg <= search[1]))[0]
    if len(idx) < 5:
        return False
    k = idx[np.argmax(smoothed[idx])]
    if k == idx[-1]:
        return False
    after = np.where((np.arange(n) > k) & (qrg <= search[1] + 3))[0]
    if len(after) == 0:
        return False
    j = after[np.argmin(smoothed[after])]

    def local_noise(c):
        return np.std(resid[max(c - 10, 0):c + 11])

    decay = smoothed[k] - smoothed[j]
    return bool(decay >= max(min_decay * smoothed[k], nsigma * max(local_noise(k), local_noise(j))))


def _maxima_persistence(y):
    """(index, persistence) of the maxima of a 1D curve (0-dimensional persistence of its superlevel sets).

    The persistence of a maximum is how far one has to descend before it merges into a higher one; the
    global maximum persists down to the curve's minimum. Small persistence = noise-sized wiggle."""
    n = len(y)
    order = np.argsort(-y, kind="stable")
    parent = -np.ones(n, dtype=int)
    peak = {}                                   # root -> index of that component's maximum

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    pairs = []
    for i in order:
        parent[i] = i
        left = i > 0 and parent[i - 1] >= 0
        right = i < n - 1 and parent[i + 1] >= 0
        if not left and not right:
            peak[i] = i                         # a new maximum is born
        elif left and right:
            rl, rr = find(i - 1), find(i + 1)
            lo, hi = (rl, rr) if y[peak[rl]] < y[peak[rr]] else (rr, rl)
            pairs.append((peak[lo], float(y[peak[lo]] - y[i])))     # the lower maximum dies here
            parent[lo] = hi
            parent[i] = hi
        else:
            parent[i] = find(i - 1 if left else i + 1)
    g = int(np.argmax(y))
    pairs.append((g, float(y[g] - y.min())))
    return pairs


def _local_noise(resid, k, half):
    """Robust local sigma of a residual curve around index k (no correction for the smoother)."""
    seg = resid[max(0, k - half):k + half + 1]
    return 1.4826*float(np.median(np.abs(seg - np.median(seg))))


def kratky_descriptors(qrg, ky, nsigma=6.0):
    """Model-free descriptors of a dimensionless Kratky curve.

    Meant as cheap hints for ordering components along a continuum
    (compact -> elongated/lobed) without choosing a model; see
    molass-researcher experiment 49d/49f/49j (the four Y17AH20N components
    collapse onto one master curve once normalized by their main peak, the
    second feature fading continuously from component 1 to 4).

    Secondary maxima are judged by their *persistence* (how far the curve
    must descend before the maximum merges into a higher one), which is the
    stable notion: noise of sup-norm size eps moves persistences by at most
    eps (Cohen-Steiner, Edelsbrunner, Harer), so a maximum with persistence
    above 2*eps cannot be a noise artifact. Persistence is measured on the
    Savitzky-Golay-smoothed curve, so eps is 3 x the *local* noise sigma of
    that smoothed curve (noise grows with q; the smoother's variance
    reduction is computed from its weights), i.e. the default ``nsigma`` = 6.

    Parameters
    ----------
    qrg, ky : ndarray
        Dimensionless q*Rg and (qRg)^2 P(q)/I(0).
    nsigma : float, optional
        A secondary maximum counts only if its persistence exceeds ``nsigma``
        times the local noise sigma of the smoothed curve at its position.
        Default 6 (= 2 x 3 sigma).

    Returns
    -------
    dict
        ``has_peak``: False if there is no interior main peak (monotone /
        elongated curves); then ``peak_qrg``, ``peak_height`` and
        ``tail_ratio`` are NaN, ``hump_prominence`` is 0.0 and ``maxima`` is
        empty -- the dict always has the same keys.
        ``peak_qrg``, ``peak_height``: main peak (smoothed) in qRg 0.5-5.
        ``tail_ratio``: curve height at 2.5 x peak_qrg relative to peak_height
        (NaN if beyond the data) -- how slowly the curve decays after the peak.
        ``hump_prominence``: persistence of the most persistent significant
        secondary maximum at 1.2-3.2 x peak_qrg, relative to peak_height (0 if
        none -- a shoulder without a maximum is not seen; ripples further out
        are form-factor oscillations of a compact body, a different feature).
        ``maxima``: list of (qrg, height, persistence) of all significant
        interior maxima, most persistent first.
    """
    qrg = np.asarray(qrg, float); ky = np.asarray(ky, float)
    n = len(ky)
    no_peak = {"has_peak": False, "peak_qrg": np.nan, "peak_height": np.nan, "tail_ratio": np.nan,
               "hump_prominence": 0.0, "maxima": []}
    w = min(15, n - (1 - n % 2))
    if w < 5:
        return no_peak
    smooth = savgol_filter(ky, w, 3)
    resid = ky - smooth
    h = savgol_coeffs(w, 3)
    sh2 = float(np.sum(h**2))
    resid_to_raw = 1.0/np.sqrt(max(1 - 2*h[w//2] + sh2, 1e-6))      # residual sigma -> raw point noise sigma
    raw_to_smooth = np.sqrt(sh2)                                    # raw noise sigma -> smoothed-curve noise sigma
    window = (qrg >= 0.5) & (qrg <= 5.0)
    if window.sum() < 5:
        return no_peak
    idx = np.where(window)[0]
    k = idx[np.argmax(smooth[idx])]
    if k == idx[-1]:
        return no_peak
    xp, yp = float(qrg[k]), float(smooth[k])

    qmax = float(qrg.max())
    tail_ratio = float(np.interp(2.5*xp, qrg, smooth)/yp) if 2.5*xp <= qmax else np.nan

    half = max(10, n//12)
    maxima = []
    for i, persistence in _maxima_persistence(smooth):
        if i in (0, n - 1):
            continue                                # a rise at the edge is not an interior maximum
        sigma_smooth = _local_noise(resid, i, half)*resid_to_raw*raw_to_smooth
        if persistence > nsigma*sigma_smooth:
            maxima.append((float(qrg[i]), float(smooth[i]), persistence))
    maxima.sort(key=lambda m: -m[2])
    humps = [m for m in maxima if 1.2*xp <= m[0] <= 3.2*xp]
    prominence = humps[0][2]/yp if humps else 0.0
    return {"has_peak": True, "peak_qrg": xp, "peak_height": yp, "tail_ratio": tail_ratio,
            "hump_prominence": float(prominence), "maxima": maxima}


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


def _match_score(component_qrg, component_ky, model_Rg, model_P_fn, qrg_window=None):
    """Heuristic similarity (NOT a statistical likelihood): exp(-normalized RMSE)
    between the component's own Kratky curve and a reference shape's curve,
    both evaluated on the component's own qRg grid within qrg_window
    (None: the module default ``QRG_MATCH_WINDOW``, looked up at call time)."""
    if qrg_window is None:
        qrg_window = QRG_MATCH_WINDOW
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


class ShapeMatchResult:
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
    best_raw_scores : list of float
        Per component, the best un-normalized match score (0-1, NaN if
        unavailable). Row normalization hides absolute quality; this tells
        whether even the best library shape is a good match (well-covered
        shapes score ~0.6-0.9, poorly covered ones ~0.2-0.4 in experiment 49b;
        no hard threshold).
    raw_score_matrix : ndarray, shape (n_components, n_shapes) or None
        The un-normalized scores (after chain / two-lobe gating) behind
        ``score_matrix``. Use ``score_matrix`` to *rank* the shapes of one
        component (it only says which shape is relatively best) and the raw
        scores / ``best_raw_scores`` to judge whether the best shape is a
        good match at all.
    qrg_window : tuple of float
        The (low, high) qRg window the scores were computed in.
    kratky_curves : list of (ndarray, ndarray) or None
        Per component, the dimensionless Kratky curve (qRg, (qRg)^2 P/I(0))
        the scores were computed from (None if Rg was unavailable). Used by
        :func:`plot_kratky_overlay`.
    descriptors : list of dict or None
        Per component, the model-free curve descriptors of
        :func:`kratky_descriptors` (None if Rg was unavailable; a curve
        without an interior peak has ``has_peak=False``).
    """

    def __init__(self, shape_names, component_labels, score_matrix, categories,
                 peak_qrgs, peak_spread, best_raw_scores=None, raw_score_matrix=None,
                 kratky_curves=None, descriptors=None, qrg_window=None):
        self.qrg_window = tuple(QRG_MATCH_WINDOW if qrg_window is None else qrg_window)
        self.shape_names = shape_names
        self.component_labels = component_labels
        self.score_matrix = score_matrix
        self.categories = categories
        self.peak_qrgs = peak_qrgs
        self.peak_spread = peak_spread
        if best_raw_scores is None:
            best_raw_scores = [np.nan]*len(component_labels)
        self.best_raw_scores = best_raw_scores
        self.raw_score_matrix = raw_score_matrix
        if kratky_curves is None:
            kratky_curves = [None]*len(component_labels)
        self.kratky_curves = kratky_curves
        if descriptors is None:
            descriptors = [None]*len(component_labels)
        self.descriptors = descriptors

    def best_shape(self, component=0):
        """Best-matching reference shape of one component.

        Parameters
        ----------
        component : int, optional
            Row index (0-based).

        Returns
        -------
        tuple
            ``(name, relative_score, raw_score)``; ``(None, nan, nan)`` if the
            component had no usable Rg. ``relative_score`` is the row-normalized
            score (ranking only), ``raw_score`` the absolute 0-1 score that
            tells whether the match is good at all.
        """
        row = self.score_matrix[component]
        if not np.isfinite(row).any():
            return None, np.nan, np.nan
        j = int(np.nanargmax(row))
        raw = np.nan if self.raw_score_matrix is None else float(self.raw_score_matrix[component, j])
        return self.shape_names[j], float(row[j]), raw

    def __repr__(self):
        lines = [f"ShapeMatchResult({len(self.component_labels)} components, "
                 f"{len(self.shape_names)} reference shapes, peak_spread={self.peak_spread})"]
        for label, cat, peak, best in zip(self.component_labels, self.categories,
                                          self.peak_qrgs, self.best_raw_scores):
            peak_str = f"{peak:.3f}" if peak is not None else "none"
            lines.append(f"  {label}: peak_qRg={peak_str}  category={cat}  best_raw_score={best:.2f}")
        return "\n".join(lines)


def compute_shape_match_scores(qv, P, sg_list, qrg_window=None):
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
    qrg_window : tuple of float, optional
        (low, high) qRg window the curves are compared in; default
        ``QRG_MATCH_WINDOW``. A window ending before a curve's second hump
        cannot see it.

    Returns
    -------
    ShapeMatchResult

    Examples
    --------
    ::

        from molass.Kratky.ShapeMatch import compute_shape_match_scores
        qv = decomp.xr.qv
        _, _, P = decomp.get_xr_matrices()[0:3]
        sg_list = [c.get_guinier_object() for c in decomp.get_xr_components()]
        result = compute_shape_match_scores(qv, P, sg_list)
        print(result)
    """
    return _match_columns(qv, [P[:, k] for k in range(len(sg_list))],
                          [sg.Rg for sg in sg_list], [sg.Iz for sg in sg_list],
                          [f"component-{k+1}" for k in range(len(sg_list))], qrg_window)


def match_kratky_curve(q, I, Rg, I0=1.0, qrg_window=None, label="curve"):
    """Match one scattering profile against the reference-shape library.

    For data that do not come from a :class:`~molass.LowRank.Decomposition.Decomposition`
    (simulated bodies, DENSS profiles, a benchmark): no Guinier objects needed.

    Parameters
    ----------
    q : ndarray
        q-values (Å⁻¹ or any unit consistent with ``Rg``).
    I : ndarray
        Scattering profile at ``q``.
    Rg : float
        Radius of gyration (in the inverse unit of ``q``).
    I0 : float, optional
        Forward scattering I(0) used to normalize the Kratky curve (default 1,
        i.e. ``I`` is already normalized).
    qrg_window : tuple of float, optional
        As in :func:`compute_shape_match_scores`.
    label : str, optional
        Row label prefix.

    Returns
    -------
    ShapeMatchResult
        With a single row; ``result.best_shape()`` gives the best match.
    """
    return _match_columns(np.asarray(q, float), [np.asarray(I, float)], [Rg], [I0], [label], qrg_window)


def _match_columns(qv, columns, rgs, izs, labels, qrg_window):
    window = tuple(QRG_MATCH_WINDOW if qrg_window is None else qrg_window)
    model_shapes = get_model_shapes()
    shape_names = [spec.name for spec in model_shapes]

    component_labels = []
    score_rows = []
    categories = []
    peak_qrgs = []
    best_raw_scores = []
    raw_rows = []
    kratky_curves = []
    descriptors = []

    for k, (profile, rg, iz) in enumerate(zip(columns, rgs, izs)):
        if rg is None or (isinstance(rg, float) and np.isnan(rg)):
            component_labels.append(f"{labels[k]} (Rg=unavailable)")
            score_rows.append(np.full(len(model_shapes), np.nan))
            raw_rows.append(np.full(len(model_shapes), np.nan))
            categories.append("Rg unavailable")
            peak_qrgs.append(None)
            best_raw_scores.append(np.nan)
            kratky_curves.append(None)
            descriptors.append(None)
            continue

        qrg = qv * rg
        ky = qrg**2 * profile / iz
        peak = kratky_peak_qrg(qv, profile, rg, iz)

        scores = np.array([_match_score(qrg, ky, spec.Rg, spec.P_fn, window)
                            for spec in model_shapes])
        # A clear interior peak rules out the (peak-less) Gaussian chain.
        if has_clear_kratky_peak(qrg, ky):
            for j, spec in enumerate(model_shapes):
                if spec.is_chain:
                    scores[j] *= CHAIN_GATE_FACTOR
        # The two-lobe entries are meant for curves with a second hump; without one they would only win
        # by the sharp minima of a monodisperse smooth body inside the wide match window (exp. 49o).
        desc = kratky_descriptors(qrg, ky)
        if desc["hump_prominence"] <= 0:
            for j, spec in enumerate(model_shapes):
                if spec.is_two_lobe:
                    scores[j] *= TWO_LOBE_GATE_FACTOR
        row_sum = np.nansum(scores)
        scores_norm = scores / row_sum if row_sum > 0 else scores

        component_labels.append(f"{labels[k]} (Rg={rg:.1f})")
        score_rows.append(scores_norm)
        raw_rows.append(scores)
        kratky_curves.append((qrg, ky))
        descriptors.append(desc)
        categories.append(classify_shape_category(peak))
        peak_qrgs.append(peak)
        best_raw_scores.append(float(np.nanmax(scores)) if np.isfinite(scores).any() else np.nan)

    valid_peaks = np.array([p for p in peak_qrgs if p is not None])
    peak_spread = float(np.std(valid_peaks)) if len(valid_peaks) > 1 else None

    return ShapeMatchResult(
        shape_names=shape_names,
        component_labels=component_labels,
        score_matrix=np.array(score_rows),
        categories=categories,
        peak_qrgs=peak_qrgs,
        peak_spread=peak_spread,
        best_raw_scores=best_raw_scores,
        raw_score_matrix=np.array(raw_rows),
        kratky_curves=kratky_curves,
        descriptors=descriptors,
        qrg_window=window,
    )


def plot_kratky_overlay(result, component, shapes=None, fig=None, qrg_max=OVERLAY_QRG_MAX,
                        residual=True):
    """Overlay a component's Kratky curve with one or more reference shapes' curves.

    This is what the match score is computed from, made visible: the shaded
    band is the match window, and the optional lower panel shows
    ``data - model`` inside it.

    Parameters
    ----------
    result : ShapeMatchResult
    component : int
        Zero-based component (row) index.
    shapes : int, list of int, or None, optional
        Shape (column) index, several indices, or None for all shapes.
    fig : matplotlib.figure.Figure, optional
        Figure to (re)draw into -- it is cleared first. If None, a new pyplot
        figure is created.
    qrg_max : float, optional
        Upper end of the displayed qRg range. Default 10.
    residual : bool, optional
        Add a residual panel under the overlay. Default True.

    Returns
    -------
    PlotResult
        ``.fig`` and ``.axes`` (the overlay Axes).

    Examples
    --------
    ::

        result = decomp.get_kratky_shape_match()
        plot_kratky_overlay(result, component=0, shapes=3)
    """
    import matplotlib.pyplot as plt
    from molass.PlotUtils.PlotResult import PlotResult

    curve = result.kratky_curves[component]
    if curve is None:
        raise ValueError(f"{result.component_labels[component]}: no Kratky curve available")
    qrg, ky = curve

    specs = get_model_shapes()
    if shapes is None:
        indices = list(range(len(specs)))
    elif isinstance(shapes, (int, np.integer)):
        indices = [int(shapes)]
    else:
        indices = [int(j) for j in shapes]

    if fig is None:
        fig = plt.figure(figsize=(7, 6 if residual else 4.5))
    else:
        fig.clear()
    if residual:
        ax, rax = fig.subplots(2, 1, sharex=True, gridspec_kw=dict(height_ratios=[3, 1]))
    else:
        ax, rax = fig.subplots(), None

    lo, hi = result.qrg_window
    shown = qrg <= qrg_max
    in_win = (qrg >= lo) & (qrg <= hi)
    grid = np.linspace(0.05, qrg_max, 400)

    ax.plot(qrg[shown], ky[shown], "o", ms=3, color="0.25", label=result.component_labels[component])
    top = np.max(ky[in_win]) if in_win.any() else np.max(ky[shown])
    for j in indices:
        spec = specs[j]
        label = spec.name
        if result.raw_score_matrix is not None:
            label += (f"  (score {result.score_matrix[component, j]:.2f}, "
                      f"raw {result.raw_score_matrix[component, j]:.2f})")
        model = grid**2 * spec.P_fn(grid/spec.Rg)
        ax.plot(grid, model, color=get_shape_color(j), lw=1.6, label=label)
        top = max(top, np.max(model[(grid >= lo) & (grid <= hi)]))
        if rax is not None and in_win.any():
            ref = qrg[in_win]**2 * spec.P_fn(qrg[in_win]/spec.Rg)
            rax.plot(qrg[in_win], ky[in_win] - ref, color=get_shape_color(j), lw=1.2)

    peak = result.peak_qrgs[component]
    if peak is not None:
        ax.axvline(peak, color="0.25", ls="--", lw=0.8)
    ax.plot([GLOBULAR_PEAK_QRG], [1.104], "k+", ms=10, label="globular peak (√3, 1.104)")
    for a in (ax, rax):
        if a is not None:
            a.axvspan(lo, hi, color="0.93", zorder=0)
    ax.set_ylim(0, 1.25*top)
    ax.set_xlim(0, qrg_max)
    ax.set_ylabel("(qRg)² P(q) / I(0)")
    ax.legend(fontsize=7, loc="upper right")
    if len(indices) == 1:
        ax.set_title(f"{result.component_labels[component]} vs {specs[indices[0]].name}")
    else:
        ax.set_title(f"{result.component_labels[component]} vs reference shapes")
    last = rax if rax is not None else ax
    last.set_xlabel("qRg")
    if rax is not None:
        rax.axhline(0, color="0.4", lw=0.6)
        rax.set_ylabel("data − model", fontsize=8)
    fig.tight_layout()
    return PlotResult(fig, ax, result=result)


def plot_kratky_series(result, fig=None, qrg_max=OVERLAY_QRG_MAX):
    """Compare the Kratky curves of all components, without choosing any model.

    Left: the curves as measured (qRg vs (qRg)^2 P/I(0)). Right: each curve
    normalized by its own main peak (x/x_peak vs y/y_peak) -- components of
    similar architecture fall onto one master curve, and a continuous
    variation (e.g. a secondary hump fading from one component to the next)
    shows up as a gradual change. The legend lists the model-free
    :func:`kratky_descriptors`.

    Parameters
    ----------
    result : ShapeMatchResult
    fig : matplotlib.figure.Figure, optional
        Figure to (re)draw into (cleared first). If None, a new pyplot figure.
    qrg_max : float, optional
        Upper end of the displayed qRg range. Default 10.

    Returns
    -------
    PlotResult
        ``.fig`` and ``.axes`` (the left, measured-curve Axes).

    Examples
    --------
    ::

        result = decomp.get_kratky_shape_match()
        plot_kratky_series(result)
    """
    import matplotlib.pyplot as plt
    from molass.PlotUtils.PlotResult import PlotResult

    if fig is None:
        fig = plt.figure(figsize=(12, 4.8))
    else:
        fig.clear()
    ax, axn = fig.subplots(1, 2)

    for k, curve in enumerate(result.kratky_curves):
        if curve is None:
            continue
        qrg, ky = curve
        shown = qrg <= qrg_max
        desc = result.descriptors[k]
        color = f"C{k}"
        label = result.component_labels[k]
        if desc is None or not desc["has_peak"]:
            ax.plot(qrg[shown], ky[shown], color=color, lw=1.2, label=f"{label}: no clear peak")
            continue
        tail = "n/a" if not np.isfinite(desc["tail_ratio"]) else f"{desc['tail_ratio']:.2f}"
        label += (f": peak {desc['peak_height']:.2f} @ {desc['peak_qrg']:.2f}, tail {tail}, "
                  f"hump +{desc['hump_prominence']:.2f}")
        ax.plot(qrg[shown], ky[shown], color=color, lw=1.2, label=label)
        ax.plot([desc["peak_qrg"]], [desc["peak_height"]], "v", color=color)
        xn = qrg/desc["peak_qrg"]
        norm_shown = shown & (xn <= 5)
        axn.plot(xn[norm_shown], ky[norm_shown]/desc["peak_height"], color=color, lw=1.2)

    ax.plot([GLOBULAR_PEAK_QRG], [1.104], "k+", ms=10)
    ax.set_xlabel("qRg"); ax.set_ylabel("(qRg)² P(q) / I(0)")
    ax.set_title("Kratky curves as measured"); ax.set_xlim(0, qrg_max); ax.set_ylim(bottom=0)
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.14))
    axn.set_xlabel("qRg / qRg of the main peak"); axn.set_ylabel("Kratky / main peak height")
    axn.set_title("normalized by each component's own peak"); axn.set_xlim(0, 5); axn.set_ylim(0, 1.2)
    fig.tight_layout()
    return PlotResult(fig, ax, result=result)


def connect_shape_match_overlay(fig, ax, result, on_dblclick=None):
    """Make a match-score heatmap respond to double-clicks.

    A double-click on a cell calls ``on_dblclick(result, component, shape)``
    with the cell's row and column indices; a double-click on a row label
    calls it with ``shape=None`` (all shapes). Needs an interactive backend
    (a plain inline notebook figure cannot receive clicks -- call
    :func:`plot_kratky_overlay` directly there).

    Parameters
    ----------
    fig, ax : matplotlib Figure and the heatmap Axes
    result : ShapeMatchResult
    on_dblclick : callable, optional
        ``f(result, component, shape)``. Default: draw :func:`plot_kratky_overlay`
        into one separate pyplot figure that is reused by later double-clicks.

    Returns
    -------
    int
        The matplotlib connection id (``fig.canvas.mpl_disconnect`` to remove).
    """
    if on_dblclick is None:
        state = {"fig": None}

        def on_dblclick(res, component, shape):
            import matplotlib.pyplot as plt
            ofig = state["fig"]
            if ofig is not None and not plt.fignum_exists(ofig.number):
                ofig = None
            state["fig"] = plot_kratky_overlay(res, component, shape, fig=ofig).fig
            state["fig"].canvas.draw_idle()
            state["fig"].show()

    n_comp, n_shapes = result.score_matrix.shape

    def hit(event):
        if event.inaxes is ax:
            if event.xdata is None or event.ydata is None:
                return None
            i, j = int(round(event.ydata)), int(round(event.xdata))
            return (i, j) if 0 <= i < n_comp and 0 <= j < n_shapes else None
        try:
            renderer = fig.canvas.get_renderer()
        except AttributeError:
            return None
        for i, label in enumerate(ax.get_yticklabels()):
            if label.get_window_extent(renderer).contains(event.x, event.y):
                return i, None
        return None

    def on_press(event):
        if not event.dblclick or event.button != 1:
            return
        cell = hit(event)
        if cell is None or result.kratky_curves[cell[0]] is None:
            return
        on_dblclick(result, *cell)

    return fig.canvas.mpl_connect("button_press_event", on_press)


def plot_shape_match(result, ax=None, title="Component x model-shape match score",
                         show_shape_key=True, on_dblclick=None, interactive=True):
    """Render a :class:`ShapeMatchResult` as a components x shapes heatmap.

    Parameters
    ----------
    result : ShapeMatchResult
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
    on_dblclick : callable, optional
        ``f(result, component, shape)`` called on a double-click on a heatmap
        cell (``shape`` = column index) or row label (``shape=None``). Default:
        open :func:`plot_kratky_overlay` in a reused pyplot figure. Only
        effective on interactive backends.
    interactive : bool, optional
        Set False to not connect any double-click handler. Default True.

    Returns
    -------
    PlotResult
        Has ``.fig``, ``.axes`` (the heatmap Axes specifically, even when the
        shape key row is also present, for consistency with other molass
        plot functions).

    Examples
    --------
    ::

        result = decomp.get_kratky_shape_match()
        plot_result = plot_shape_match(result)
        plot_result.fig.show()
    """
    import matplotlib.pyplot as plt
    from molass.PlotUtils.PlotResult import PlotResult

    n_shapes = len(result.shape_names)
    matrix = result.score_matrix
    vmax = np.nanmax(matrix) if np.isfinite(matrix).any() else 1.0

    own_fig = ax is None
    if own_fig:
        height = 0.6*len(result.component_labels) + 1.5
        if show_shape_key:
            from molass.Kratky.ShapeKey import get_shape_key_image
            key_image = get_shape_key_image()
            key_height = 1.3  # fixed, independent of the cached image's raw pixel size
            cbar_width = 0.35  # dedicated colorbar column -- kept OUT of the n_shapes
                               # equal-width columns so the icon row and heatmap span
                               # exactly the same width and align 1:1, column by column
            fig = plt.figure(figsize=(11 + cbar_width, height + key_height))
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
            fig, ax = plt.subplots(figsize=(11, height))
            im = ax.imshow(matrix, cmap="viridis", aspect="auto", vmin=0, vmax=vmax)
            fig.colorbar(im, ax=ax, label="relative match score (row-normalized)")
    else:
        fig = ax.figure
        im = ax.imshow(matrix, cmap="viridis", aspect="auto", vmin=0, vmax=vmax)
        fig.colorbar(im, ax=ax, label="relative match score (row-normalized)")

    ax.set_xticks(range(n_shapes))
    ax.set_xticklabels(result.shape_names, rotation=30, ha="right")
    ax.set_yticks(range(len(result.component_labels)))
    # Row normalization hides absolute quality, so show the best raw score next to each label.
    ylabels = [f"{label}\nbest raw {best:.2f}" if np.isfinite(best) else label
               for label, best in zip(result.component_labels, result.best_raw_scores)]
    ax.set_yticklabels(ylabels, fontsize=8)
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

    if interactive:
        connect_shape_match_overlay(fig, ax, result, on_dblclick=on_dblclick)
        if own_fig:
            fig.text(0.5, 0.005, "double-click a cell to overlay the Kratky plots "
                     "(row label: all shapes)", ha="center", va="bottom", fontsize=7, color="0.4")

    return PlotResult(fig, ax, result=result)


