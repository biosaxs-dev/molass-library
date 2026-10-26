"""
    Homogeneity.Report.py

    The composed homogeneity analysis: concentration proxies, a set of ratio curves,
    automatic peak cores and descriptive flatness statistics, with no pure/impure verdict.
"""
import re
import numpy as np
from molass.Homogeneity.Proxies import xr_i0_proxy, xr_q_proxy, uv_proxy
from molass.Homogeneity.Ratios import ProxyRatio, independent_axes

DEFAULT_WAVELENGTHS = (260, 280, 290, 320)
_Q_NAME = re.compile(r"^I\((?!0\))(.+)\)$")
_A_NAME = re.compile(r"^A(\d+(?:\.\d+)?)$")


def find_cores(frames, y, frac=0.30, prominence=0.10):
    """Peak cores of a concentration curve: for each peak, the contiguous frames above
    ``frac`` of the peak height, limited by the valleys to the neighbouring peaks.

    Returns a list of ``(first_frame, last_frame)``.
    """
    from scipy.signal import find_peaks
    frames = np.asarray(frames)
    y = np.where(np.isfinite(y), y, 0.0)
    ys = np.convolve(y, np.ones(3) / 3, mode="same")
    peaks, _ = find_peaks(ys, prominence=prominence * ys.max())
    if len(peaks) == 0:
        peaks = np.array([int(np.argmax(ys))])
    bounds = [0] + [int(a + np.argmin(ys[a:b + 1])) for a, b in zip(peaks[:-1], peaks[1:])] + [len(ys) - 1]
    cores = []
    for k, p in enumerate(peaks):
        lo, hi, thr = bounds[k], bounds[k + 1], frac * ys[p]
        a = p
        while a > lo and ys[a - 1] > thr:
            a -= 1
        b = p
        while b < hi and ys[b + 1] > thr:
            b += 1
        cores.append((int(frames[a]), int(frames[b])))
    return cores


def _ratio_scale(ratio, core_mask_):
    # ratios near 0 (e.g. A320/A280 of a few percent) are reported in absolute units
    med = np.nanmedian(ratio.values[core_mask_])
    return 1.0 if abs(med) < 0.05 else "median"


class HomogeneityResult:
    """Result of :meth:`SecSaxsData.homogeneity`.

    Attributes
    ----------
    frames : np.ndarray
    proxies : dict
        name -> :class:`ConcentrationProxy` (only the ones used by the selected pairs).
    pairs : list of (str, str)
        The selected (numerator, denominator) names.
    ratios : dict
        ratio name -> :class:`ProxyRatio`.
    cores : list of (int, int)
        Peak cores (first and last frame).
    stats : dict
        ``(core_index, ratio_name)`` -> :class:`Flatness`.
    q1, q2 : float
        The q values (1/A) behind the default ``I(q1)``, ``I(q2)``.
    delta : float
        Shift of the UV->XR mapping in XR frames (+ = later) used for the UV proxies.
    skipped : list of str
        Requested ratios that could not be made (missing UV, wavelength out of range ...).
    independent_axes : int
        Number of independent axes among the ratios (see :func:`independent_axes`).

    Notes
    -----
    Descriptive only: there is no pure/impure verdict. XR/UV ratios depend on the
    UV->XR mapping (``depends_on_mapping``); XR-only and UV-only ratios do not, which makes
    them a check on the cross ratios. A mapping error shows as a tilt of the cross ratios,
    a concentration-dependent effect as a curvature (symmetric peaks).
    """

    def __init__(self, ssd, pairs, delta, q1, q2, cores, rgcurve, min_score):
        self._ssd, self._rgcurve, self._min_score = ssd, rgcurve, min_score
        self.pairs, self.delta, self.q1, self.q2 = list(pairs), delta, q1, q2
        self.frames = np.asarray(ssd.xr.jv)
        self.cores = list(cores)
        self.proxies, self.ratios, self.skipped = {}, {}, []
        for a, b in self.pairs:
            try:
                ra, rb = self._proxy(a), self._proxy(b)
            except ValueError as exc:
                self.skipped.append(f"{a}/{b}: {exc}")
                continue
            r = ProxyRatio(ra, rb)
            self.ratios[r.name] = r
        self.stats = {}
        for k, (f0, f1) in enumerate(self.cores):
            m = (self.frames >= f0) & (self.frames <= f1)
            for name, r in self.ratios.items():
                if np.isfinite(r.values[m]).sum() >= 4:
                    self.stats[(k, name)] = r.flatness((f0, f1), scale=_ratio_scale(r, m))

    def _proxy(self, name):
        if name in self.proxies:
            return self.proxies[name]
        ssd = self._ssd
        if name == "I(0)":
            if self._rgcurve is None:
                raise ValueError("no Rg curve")
            p = xr_i0_proxy(self._rgcurve, min_score=self._min_score)
        elif _Q_NAME.match(name):
            p = xr_q_proxy(ssd.xr, float(_Q_NAME.match(name).group(1)))
        elif _A_NAME.match(name):
            if ssd.uv is None:
                raise ValueError("no UV data")
            w = float(_A_NAME.match(name).group(1))
            if not ssd.uv.wv[0] <= w <= ssd.uv.wv[-1]:
                raise ValueError(f"{w:g} nm is outside the UV range")
            p = uv_proxy(ssd.uv, w, ssd.get_mapping(), self.frames, delta=self.delta)
        else:
            raise KeyError(f"unknown proxy name {name!r}; use I(0), I(<q>) or A<wavelength>")
        self.proxies[name] = p
        return p

    @property
    def independent_axes(self):
        return independent_axes(self.ratios.values())

    def is_classical(self, name):
        return self.ratios[name].numerator.name == "I(0)"

    def shifted(self, delta):
        """The same analysis with the UV->XR mapping shifted by ``delta`` XR frames (+ = later)."""
        return HomogeneityResult(self._ssd, self.pairs, delta, self.q1, self.q2, self.cores,
                                 self._rgcurve, self._min_score)

    def reselect(self, pairs):
        """The same analysis (cores, q values, shift) with a different set of ``(numerator, denominator)`` names."""
        return HomogeneityResult(self._ssd, pairs, self.delta, self.q1, self.q2, self.cores,
                                 self._rgcurve, self._min_score)

    def table(self):
        """Rows (dicts) of the statistics: core, first, last, ratio, mapping dependence and the Flatness fields."""
        rows = []
        for (k, name), f in self.stats.items():
            f0, f1 = self.cores[k]
            rows.append(dict(core=k + 1, first=f0, last=f1, ratio=name,
                             depends_on_mapping=self.ratios[name].depends_on_mapping,
                             classical=self.is_classical(name), **f.asdict()))
        return rows

    def summary(self):
        lines = [f"{len(self.ratios)} ratios, {self.independent_axes} independent axes; mapping shift {self.delta:+g} frame"
                 f"; cross ratios (*) depend on the mapping; classical = I(0) numerator (c)"]
        for k, (f0, f1) in enumerate(self.cores):
            lines.append(f"\ncore {k + 1}: frames {f0}-{f1}")
            lines.append(f"{'ratio':22s} {'median':>9s} {'SD':>7s} {'noise':>7s} {'SD/noise':>9s} {'tilt':>7s} {'tilt z':>7s} {'curv.':>7s}")
            for name in self.ratios:
                f = self.stats.get((k, name))
                if f is None:
                    continue
                tag = ("*" if self.ratios[name].depends_on_mapping else " ") + ("c" if self.is_classical(name) else " ")
                lines.append(f"{name + ' ' + tag:22s} {f.median:9.4g} {f.sd:7.1%} {f.noise:7.1%} {f.sd_over_noise:9.1f}"
                             f" {f.tilt:+7.1%} {f.tilt_z:7.1f} {f.curvature:+7.1%}")
        for s in self.skipped:
            lines.append(f"skipped {s}")
        return "\n".join(lines)

    def __repr__(self):
        return f"HomogeneityResult({len(self.ratios)} ratios, {len(self.cores)} cores, delta={self.delta:g})"

    def plot(self, ylim=(-40, 40), pad=8, figsize=(12, 7)):
        """Elution curves (top) and the deviation of each ratio from its core median (bottom).

        Classical ratios (I(0) numerator) are drawn black/gray and thick; ratios that depend on
        the mapping are dashed. Returns the figure.
        """
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True, gridspec_kw=dict(height_ratios=[1, 2]))
        for name in ("A280", "I(0)"):
            p = self.proxies.get(name)
            if p is not None and np.isfinite(p.values).any():
                ax1.plot(p.frames, p.values / np.nanmax(p.values), label=name)
        xr_curve = self._ssd.xr.get_icurve()
        ax1.plot(xr_curve.x, xr_curve.y / xr_curve.y.max(), color="0.7", lw=1, label="XR curve")
        ax1.set_ylabel("normalised"); ax1.legend(fontsize=8)
        classical_colors = iter(["k", "0.45"])
        for name, r in self.ratios.items():
            y = np.full(len(self.frames), np.nan)
            for k, (f0, f1) in enumerate(self.cores):
                m = (self.frames >= f0) & (self.frames <= f1)
                if (k, name) not in self.stats:
                    continue
                dev = r.deviation((f0, f1), scale=_ratio_scale(r, m))
                w = (self.frames >= f0 - pad) & (self.frames <= f1 + pad) & np.isnan(y)
                y[w] = dev[w]
            kw = dict(ls="--" if r.depends_on_mapping else "-", lw=1.2)
            if self.is_classical(name):
                kw.update(color=next(classical_colors), lw=2.2)
            ax2.plot(self.frames, 100 * y, label=name + (" *" if r.depends_on_mapping else ""), **kw)
        for ax in (ax1, ax2):
            for f0, f1 in self.cores:
                ax.axvspan(f0, f1, color="0.93", zorder=0)
        ax2.axhline(0, color="gray", lw=0.8)
        ax2.set_ylim(*ylim)
        xs = [f for c in self.cores for f in c]
        ax2.set_xlim(min(xs) - pad, max(xs) + pad)
        ax2.set_xlabel("XR frame"); ax2.set_ylabel("deviation from the core median (%)")
        ax2.set_title(f"* depends on the UV->XR mapping (shift {self.delta:+g} frame); {self.independent_axes} independent axes",
                      fontsize=9)
        ax2.legend(fontsize=8, ncol=3)
        fig.tight_layout()
        return fig


def default_pairs(q1, q2, has_uv):
    names = [("I(0)", f"I({q1:g})"), ("I(0)", "A280"), (f"I({q1:g})", f"I({q2:g})"),
             ("A260", "A280"), ("A280", "A290"), ("A320", "A280")]
    return [p for p in names if has_uv or not any(n.startswith("A") for n in p)]


def compute_homogeneity(ssd, pairs=None, delta=0.0, q1=None, q2=None, cores=None, rgcurve=None, min_score=0.5):
    """Implementation of :meth:`SecSaxsData.homogeneity`."""
    if rgcurve is None:
        rgcurve = ssd.get_rg_curve()
    has_uv = ssd.uv is not None
    frames = np.asarray(ssd.xr.jv)
    if has_uv and ssd.uv.wv[0] <= 280 <= ssd.uv.wv[-1]:
        conc = uv_proxy(ssd.uv, 280, ssd.get_mapping(), frames, delta=delta).values
    else:
        conc = np.asarray(ssd.xr.get_icurve().y, dtype=float)
    if cores is None:
        cores = find_cores(frames, conc)
    if q1 is None:
        rgs = np.asarray(rgcurve.rgs, dtype=float)[np.asarray(rgcurve.scores, dtype=float) >= min_score]
        rgs = rgs[np.isfinite(rgs)]
        rg = np.median(rgs) if len(rgs) else 30.0
        q1 = float(np.clip(round(0.7 / rg, 3), 1.05 * ssd.xr.qv[0], 0.5 * ssd.xr.qv[-1]))
    if q2 is None:
        q2 = round(3 * q1, 3)
    if pairs is None:
        pairs = default_pairs(q1, q2, has_uv)
    return HomogeneityResult(ssd, pairs, delta, q1, q2, cores, rgcurve, min_score)
