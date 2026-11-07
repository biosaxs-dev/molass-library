"""
    Continuity.Report.py

    The continuity report (molass-library#370): does a decomposition describe a few distinct
    species, or slices of a continuous distribution?

    This is the deterministic, traditional route (fixed indicators, fixed and overridable
    thresholds, no simulation, no AI). It reports numbers and the regime in which they are
    meaningful, and gives a verdict only in the cautious three-way form below. A per-dataset
    simulation (a "digital twin" turning the numbers into likelihood ratios) is deliberately not
    part of it; see molass-researcher experiments 51p-51r.
"""
import numpy as np
from molass.Continuity.Indicators import (rg_point_noise, rg_drop, plateau_excess, find_plateaus,
                                          kratky_separation)

VERDICT_DISCRETE = "discrete"
VERDICT_NO_EVIDENCE = "no evidence for distinct species"
VERDICT_UNDETERMINED = "undetermined"

# Defaults and where they come from (molass-researcher experiments/51_paper_m_results)
DEFAULT_THRESHOLDS = dict(
    score_min=0.6,                  # Guinier score filter of RgCurve.reliable()
    intensity_frac=0.05,            # frames below this fraction of the elution maximum are ignored
    tol=1.5,                        # a constant fits a run if RSS <= tol*(n-1)*sigma^2
    min_frames=10,                  # shortest plateau
    min_points=20,                  # fewest reliable frames for any statement
    power_min=5.0,                  # Rg drop in noise units below which nothing can be said
    power_adequate=20.0,            # below this a small staircase still looks like a ramp (51m)
    excess_min=2.0,                 # plateau excess for "clear": real discrete 2.5-3.8, benchmark 2.4-5.6,
                                    # continua <= 1.6 (51m, 51n, 51o, 51r)
    separation_ref=6.0,             # Kratky separation (noise units) called "shapes differ" (51o)
    ordering_threshold=0.85,        # end_fraction above this: ordered along the elution (51n)
    ordering_min_components=4,      # ordering is only assessed from this many components (51o)
)


class ContinuityReport:
    """Result of :meth:`Decomposition.get_continuity_report`.

    The verdict has three forms and is never "continuum": a continuum can only be *not excluded*.

    - ``"discrete"``: plateaus in the data Rg curve are clear (plateau excess >= ``excess_min``).
      A positive finding, reliable in the benchmark tests.
    - ``"no evidence for distinct species"``: no clear plateau although the Rg drop is large
      enough to look for one. Weak evidence at best: with a small drop (``power`` below
      ``power_adequate``) a staircase still looks like a ramp.
    - ``"undetermined"``: too few reliable frames or an Rg drop below ``power_min`` noise units.

    Attributes
    ----------
    verdict : str
    reason : str
        One sentence saying why.
    n_frames : int
        Reliable frames behind the Rg indicators.
    drop, noise : float
        Total Rg drop (Å) and single-frame Rg noise (Å) of the data Rg curve.
    power : float
        ``drop/noise``: how many noise units the Rg drop spans. Whether the question is
        answerable at all.
    excess : float
        Plateau excess of the data Rg curve (see :func:`molass.Continuity.Indicators.plateau_excess`).
    plateaus : list of dict
        ``start``, ``stop``, ``length``, ``level`` of each plateau found.
    component_rgs : list of float or None
    plateau_backed : list of bool or None
        Per component, whether a plateau level lies within max(3 %, 1 Å) of its Rg.
    n_components : int or None
    max_separation : float
        Largest pairwise difference between the Kratky curves of the components, in noise units.
        It measures how different the *shapes* are; not discreteness.
    end_fraction : float
        Separation of the first and the last component divided by ``max_separation`` (NaN below
        ``ordering_min_components`` components).
    best_shapes : list of str or None
        Best-matching library shape of each component.
    frames, rgs : np.ndarray
        The reliable points of the data Rg curve the indicators were computed from.
    component_extents : list of (float, float) or None
        Per component the mean frame and standard deviation of its elution curve (drawn as the
        extent of the component in :meth:`plot`).
    elution : (np.ndarray, np.ndarray) or None
        The XR elution curve (frames, intensity), the background of :meth:`plot`.
    kratky_curves : list of (qrg, ky) or None
        The dimensionless Kratky curve of each component (panel b of :meth:`plot`).
    heading : str or None
        The ``dataset | model | method`` line of the decomposition, the same as the title of
        ``plot_components``.
    thresholds : dict
        The thresholds used (:data:`DEFAULT_THRESHOLDS` with the overrides).
    notes : list of str
        What the numbers mean in this case, including the limits of the verdict.
    """

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def plot(self, ax=None, fig=None, title=None):
        """Plot the evidence behind the verdict.

        (a) The Rg of the data, frame by frame (reliable frames only), on the elution curve (grey),
        with the plateaus found (red bars) and the Rg of each component drawn over its elution
        extent (mean +- one standard deviation of its elution curve). A mixture of distinct species
        shows flat stretches in the data Rg where one species dominates; a continuum a ramp.
        (b) The dimensionless Kratky plots of the components (drawn when ``fig`` is used and the
        report has them): curves that coincide mean the same particle shape.

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Draw panel (a) only, into this axes.
        fig : matplotlib.figure.Figure, optional
            Draw both panels into this figure (cleared first); ignored if ``ax`` is given.
            If neither is given a new figure is made.
        title : str, optional
            The heading of the figure (suptitle); default :attr:`heading`, i.e. the
            ``dataset | model | method`` line of ``plot_components``. A second line says how the
            Rg frames were selected.

        Returns
        -------
        molass.PlotUtils.PlotResult.PlotResult
        """
        import matplotlib.pyplot as plt
        from molass.PlotUtils.PlotResult import PlotResult

        has_kratky = ax is None and any(c is not None for c in (self.kratky_curves or []))
        if ax is None:
            if fig is None:
                fig = plt.figure(figsize=(11.5, 4.8))
            else:
                fig.clear()
            axes = list(fig.subplots(1, 2)) if has_kratky else [fig.subplots()]
        else:
            fig = ax.figure
            axes = [ax]
        self._plot_rg(axes[0], panel_label="(a) " if has_kratky else "")
        if has_kratky:
            self._plot_kratky(axes[1])

        if ax is None:
            t = self.thresholds
            lines = [title if title is not None else self.heading,
                     f"continuity report | Rg frames: Guinier score \u2265 {t['score_min']:g}, "
                     f"intensity \u2265 {t['intensity_frac']:.0%} of the maximum"]
            fig.suptitle("\n".join(s for s in lines if s), fontsize=10)
            fig.tight_layout(rect=(0, 0, 1, 0.93))
        else:
            if title is not None:
                ax.set_title(title, fontsize=10)
            fig.tight_layout()
        return PlotResult(fig, axes if len(axes) > 1 else axes[0])

    def _plot_rg(self, ax, panel_label=""):
        t_lo, t_hi = float(np.min(self.frames)), float(np.max(self.frames))
        extents = self.component_extents
        if extents:
            t_lo = min(t_lo, min(m - s for m, s in extents))
            t_hi = max(t_hi, max(m + s for m, s in extents))
        if self.elution is not None:
            x, y = (np.asarray(v, dtype=float) for v in self.elution)
            back = ax.twinx()
            back.fill_between(x, 0, y/np.max(y), color="0.9", zorder=0)
            back.set_ylim(0, 4)                  # the elution curve fills the lower quarter
            back.set_yticks([])
            ax.set_zorder(back.get_zorder() + 1)
            ax.patch.set_visible(False)
        ax.plot(self.frames, self.rgs, "o", ms=3.5, color="0.35", label="data, per frame")
        for k, p in enumerate(self.plateaus):
            ax.hlines(p["level"], p["start"], p["stop"], colors="k", lw=7, alpha=0.35, zorder=2,
                      label="plateau" if k == 0 else None)
        for k, rg in enumerate(self.component_rgs or []):
            label = f"component {k + 1}"
            if extents:
                mean, sd = extents[k]
                ax.plot([mean - sd, mean + sd], [rg, rg], lw=4, color=f"C{k}", solid_capstyle="butt",
                        label=label, zorder=3)
            else:
                ax.axhline(rg, color=f"C{k}", ls=":", lw=1.5, label=label)
        pad = 0.03*(t_hi - t_lo)
        ax.set_xlim(t_lo - pad, t_hi + pad)
        ax.set_xlabel("frame")
        ax.set_ylabel("Rg (\u00c5)")
        ax.set_title(f"{panel_label}Rg of the data and of the components: {self.verdict}", loc="left", fontsize=10)
        f = lambda v, fmt: "n/a" if not np.isfinite(v) else format(v, fmt)
        ax.text(0.02, 0.03, f"total drop {f(self.drop, '.1f')} \u00c5, noise of one frame {f(self.noise, '.2f')} \u00c5\n"
                            f"plateau excess {f(self.excess, '.2f')}, power {f(self.power, '.1f')} noise units",
                transform=ax.transAxes, fontsize=8, va="bottom", zorder=5)
        ax.legend(loc="upper right", fontsize=8)

    def _plot_kratky(self, ax):
        top = 1.4
        for k, curve in enumerate(self.kratky_curves):
            if curve is None:
                continue
            qrg, ky = (np.asarray(v, dtype=float) for v in curve)
            rg = self.component_rgs[k] if self.component_rgs is not None and k < len(self.component_rgs) else None
            label = f"component {k + 1}" + (f", Rg = {rg:.1f} \u00c5" if rg is not None and np.isfinite(rg) else "")
            ax.plot(qrg, ky, color=f"C{k}", lw=1.5, label=label)
            shown = ky[qrg <= 6]
            if len(shown):
                top = max(top, 1.1*float(np.nanmax(shown)))
        ax.axvline(np.sqrt(3), color="0.7", ls=":", lw=1)      # maximum of a compact globular particle
        ax.axhline(3/np.e, color="0.7", ls=":", lw=1)
        ax.set_xlim(0, 6)
        ax.set_ylim(0, top)
        ax.set_xlabel("qRg")
        ax.set_ylabel("(qRg)$^2$ I(q) / I(0)")
        ax.set_title("(b) Kratky plots of the components", loc="left", fontsize=10)
        ax.legend(loc="upper right", fontsize=8)

    def to_dict(self):
        """JSON-serializable form (NaN as ``None``)."""
        return {k: _json_safe(v) for k, v in self.__dict__.items()}

    def __repr__(self):
        t = self.thresholds
        f = lambda v, fmt: "n/a" if v is None or not np.isfinite(v) else format(v, fmt)
        lines = [f"ContinuityReport: {self.verdict.upper()}", f"  {self.reason}"]
        lines.append(f"  Rg curve: {self.n_frames} reliable frames, drop {f(self.drop, '.1f')} A, "
                     f"noise {f(self.noise, '.2f')} A, power {f(self.power, '.1f')} noise units "
                     f"(undetermined below {t['power_min']:g}; small staircases invisible below ~{t['power_adequate']:g})")
        lines.append(f"  plateau excess {f(self.excess, '.2f')} (clear from {t['excess_min']:g}), "
                     f"{len(self.plateaus)} plateau(s)" + "".join(
                         f"\n    frames {p['start']:.0f}-{p['stop']:.0f}: Rg {p['level']:.1f} A" for p in self.plateaus))
        if self.n_components:
            rgs = ", ".join(f"{r:.1f}" + ("*" if b else "") for r, b in zip(self.component_rgs, self.plateau_backed))
            lines.append(f"  components ({self.n_components}), Rg [A] (* = on a plateau): {rgs}")
            if self.best_shapes is not None:
                lines.append("  best library shapes: " + ", ".join(str(s) for s in self.best_shapes))
            lines.append(f"  Kratky separation max {f(self.max_separation, '.1f')} noise units, "
                         f"end fraction {f(self.end_fraction, '.2f')}")
        lines += [f"  - {note}" for note in self.notes]
        return "\n".join(lines)


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def compute_continuity_report(frames, rgs, component_rgs=None, kratky_curves=None, best_shapes=None,
                              component_extents=None, elution=None, heading=None, **thresholds):
    """Continuity report from arrays (the engine behind :meth:`Decomposition.get_continuity_report`).

    Parameters
    ----------
    frames, rgs : array-like
        The reliable points of the data Rg curve (``RgCurve.reliable()``), sorted by frame.
    component_rgs : list of float, optional
        Rg of each component, in elution order.
    kratky_curves : list of (qrg, ky), optional
        Dimensionless Kratky curve of each component (``ShapeMatchResult.kratky_curves``).
    best_shapes : list of str, optional
    component_extents : list of (mean, sd), optional
        Mean frame and standard deviation of the elution curve of each component (for the plot only).
    elution : (frames, intensity), optional
        The XR elution curve (for the plot only).
    heading : str, optional
        The ``dataset | model | method`` line of the decomposition (for the plot only).
    **thresholds
        Overrides of :data:`DEFAULT_THRESHOLDS`.

    Returns
    -------
    ContinuityReport
    """
    unknown = set(thresholds) - set(DEFAULT_THRESHOLDS)
    if unknown:
        raise TypeError(f"unknown threshold(s): {sorted(unknown)}; known: {sorted(DEFAULT_THRESHOLDS)}")
    t = {**DEFAULT_THRESHOLDS, **thresholds}
    frames = np.asarray(frames, dtype=float)
    rgs = np.asarray(rgs, dtype=float)
    notes = []

    n = len(rgs)
    noise = rg_point_noise(frames, rgs) if n >= 2 else np.nan
    usable = n >= t["min_points"] and np.isfinite(noise) and noise > 0
    drop = rg_drop(rgs) if n else np.nan
    power = drop/noise if usable else np.nan
    excess, plateaus = np.nan, []
    if usable:
        excess = plateau_excess(frames, rgs, t["tol"], sigma=noise)
        plateaus = find_plateaus(frames, rgs, sigma=noise, tol=t["tol"], min_excess=1.5, min_frames=t["min_frames"])

    if not usable:
        verdict = VERDICT_UNDETERMINED
        reason = f"Only {n} reliable Rg frames (at least {t['min_points']} with measurable noise are needed)."
    elif power < t["power_min"]:
        verdict = VERDICT_UNDETERMINED
        reason = f"The Rg drop is {power:.1f} noise units (< {t['power_min']:g}): too small to look for plateaus."
    elif plateaus and excess >= t["excess_min"]:
        verdict = VERDICT_DISCRETE
        reason = f"The data Rg curve has {len(plateaus)} plateau(s), plateau excess {excess:.2f} >= {t['excess_min']:g}."
    else:
        verdict = VERDICT_NO_EVIDENCE
        reason = f"No clear plateau in the data Rg curve (plateau excess {excess:.2f} < {t['excess_min']:g})."
        notes.append("This is not evidence of a continuum: a continuum can only be not excluded.")
        if power < t["power_adequate"]:
            notes.append(f"Low power ({power:.1f} noise units): a staircase with a small Rg drop is not "
                         f"distinguishable from a ramp, so the absence of plateaus is weak evidence.")

    component_rgs = None if component_rgs is None else [float(r) for r in component_rgs]
    n_components = None if component_rgs is None else len(component_rgs)
    backed = None
    if component_rgs is not None:
        levels = np.array([p["level"] for p in plateaus])
        backed = [bool(len(levels) and np.min(np.abs(levels - r)) <= max(0.03*r, 1.0)) for r in component_rgs]

    max_sep, end_fraction = np.nan, np.nan
    if kratky_curves is not None:
        ks = kratky_separation(kratky_curves)
        max_sep = ks["max_sep"]
        if len(kratky_curves) >= t["ordering_min_components"]:
            end_fraction = ks["end_fraction"]
        if np.isfinite(max_sep):
            if max_sep > t["separation_ref"]:
                notes.append(f"The component Kratky curves differ ({max_sep:.1f} noise units). This measures "
                             f"the spread of shapes, not discreteness: a wide continuum differs as much.")
            else:
                notes.append(f"No difference between the component Kratky curves ({max_sep:.1f} noise units): "
                             f"consistent with slices of one kind of particle, but also with discrete species "
                             f"of the same shape family.")
        if np.isfinite(end_fraction) and end_fraction >= t["ordering_threshold"]:
            notes.append(f"The components form a series ordered along the elution (end fraction "
                         f"{end_fraction:.2f}), as slices of a one-parameter family do.")
        elif len(kratky_curves) < t["ordering_min_components"]:
            notes.append(f"Ordering along the elution is not assessed with fewer than "
                         f"{t['ordering_min_components']} components.")

    return ContinuityReport(
        verdict=verdict, reason=reason, n_frames=int(n), drop=drop, noise=noise, power=power,
        excess=excess, plateaus=plateaus, component_rgs=component_rgs, plateau_backed=backed,
        n_components=n_components, max_separation=max_sep, end_fraction=end_fraction,
        best_shapes=None if best_shapes is None else list(best_shapes), thresholds=t, notes=notes,
        frames=frames, rgs=rgs,
        component_extents=None if component_extents is None else [(float(m), float(s)) for m, s in component_extents],
        elution=None if elution is None else (np.asarray(elution[0], dtype=float), np.asarray(elution[1], dtype=float)),
        kratky_curves=kratky_curves, heading=heading)


def _plot_inputs_of(decomposition):
    """Component extents, elution curve and heading, which only the plot needs. A failure here
    must not cost the verdict, so each is optional (None)."""
    extents = heading = None
    try:
        extents = decomposition.get_component_extents()
    except Exception:
        pass
    try:
        from molass.PlotUtils.DecompositionPlot import make_auto_title
        heading = make_auto_title(decomposition)
    except Exception:
        pass
    icurve = decomposition.xr_icurve
    return extents, (icurve.x, icurve.y), heading


def compute_continuity_report_of(decomposition, rgcurve=None, shapes=None, **thresholds):
    """Continuity report of a :class:`~molass.LowRank.Decomposition.Decomposition`.

    ``rgcurve`` is the data Rg curve; ``decomposition.get_rg_curve()`` (cached) if not given.
    ``shapes``: add the best-matching library shape of each component -- ``None``: only if the shape
    match is already computed (the library takes about 30 s on first use), ``True``: compute it,
    ``False``: never.
    """
    t = {**DEFAULT_THRESHOLDS, **thresholds}
    frames, rgs = decomposition.get_reliable_rg(score_min=t["score_min"], intensity_frac=t["intensity_frac"],
                                                rgcurve=rgcurve)
    best = None
    if shapes is True or (shapes is None and getattr(decomposition, '_kratky_shape_match', None) is not None):
        match = decomposition.get_kratky_shape_match()
        best = [match.best_shape(k)[0] for k in range(len(match.component_labels))]
    extents, elution, heading = _plot_inputs_of(decomposition)
    return compute_continuity_report(frames, rgs, component_rgs=decomposition.get_rgs(),
                                     kratky_curves=decomposition.get_kratky_curves(), best_shapes=best,
                                     component_extents=extents, elution=elution, heading=heading, **thresholds)
