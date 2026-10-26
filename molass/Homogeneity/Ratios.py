"""
    Homogeneity.Ratios.py

    Ratio curves of two concentration proxies and their flatness statistics.

    A ratio of two proxies is constant across the elution of a single species and
    changes where the composition changes. Which difference between species it is
    sensitive to depends on the proxies (size for I(0)/I(q), spectrum for
    A260/A280, mass per absorbance for I(0)/A280 ...).
    The statistics are descriptive: no pure/impure verdict is made here.
"""
from dataclasses import dataclass, asdict
import numpy as np
from molass.DataObjects.Curve import Curve


def core_mask(frames, core=None):
    """Boolean mask for ``core``: None (all frames), ``(first, last)`` inclusive frame
    numbers, or a boolean array of the length of ``frames``."""
    frames = np.asarray(frames)
    if core is None:
        return np.ones(len(frames), dtype=bool)
    if isinstance(core, tuple) and len(core) == 2:
        return (frames >= core[0]) & (frames <= core[1])
    mask = np.asarray(core, dtype=bool)
    if mask.shape != frames.shape:
        raise ValueError("a boolean core must have the length of the frames")
    return mask


@dataclass(frozen=True)
class Flatness:
    """Descriptive statistics of a ratio over a core.

    Attributes
    ----------
    n : int
        Number of finite points used.
    median : float
        Median of the ratio.
    sd : float
        Standard deviation relative to ``scale`` (the median, unless given).
    noise : float
        White-noise standard deviation (from second differences, insensitive to smooth
        trends), relative to ``scale``; NaN if no three consecutive frames are available.
    sd_over_noise : float
        ``sd / noise``; close to 1 when the ratio varies no more than its noise.
    tilt : float
        Linear trend across the core (end minus start), relative to ``scale``.
    tilt_z : float
        Slope divided by its standard error for white noise ``noise``.
    tilt_quad : float
        Tilt from a quadratic fit ``y = a + b*t + c*t**2`` on ``t`` in [-1, 1] across the core:
        ``2*b / scale`` (end minus start); NaN with fewer than 5 points.
    curvature : float
        ``c / scale`` of the same fit: the value at the core ends minus the value at the centre
        (positive = a dip at the centre, negative = a hump).
        A mapping error gives a tilt with curvature near 0, a concentration-dependent
        effect a curvature with tilt near 0 (symmetric peaks).
    """
    n: int
    median: float
    sd: float
    noise: float
    sd_over_noise: float
    tilt: float
    tilt_z: float
    tilt_quad: float = np.nan
    curvature: float = np.nan

    def asdict(self):
        return asdict(self)


def _scale_of(median, scale):
    s = abs(median) if scale == "median" else abs(float(scale))
    if not s > 0:
        raise ValueError("the scale is zero; pass a nonzero scale (e.g. 1.0 for a ratio near 0)")
    return s


class ProxyRatio(Curve):
    """The ratio ``numerator / denominator`` of two :class:`ConcentrationProxy` objects.

    Values are NaN where the denominator is not positive or either value is not finite.

    Attributes
    ----------
    name : str
        ``"<numerator>/<denominator>"``.
    numerator, denominator : ConcentrationProxy
    depends_on_mapping : bool
        True for XR/UV ratios, whose values change with the UV->XR mapping; XR/XR and UV/UV
        ratios are mapping-free.
    """

    def __init__(self, numerator, denominator):
        if not np.array_equal(numerator.frames, denominator.frames):
            raise ValueError("the proxies must be defined on the same frames")
        num, den = numerator.values, denominator.values
        with np.errstate(divide="ignore", invalid="ignore"):
            y = np.where(np.isfinite(num) & np.isfinite(den) & (den > 0), num / den, np.nan)
        super().__init__(np.asarray(numerator.frames), y)
        self.numerator = numerator
        self.denominator = denominator
        self.name = f"{numerator.name}/{denominator.name}"

    @property
    def frames(self):
        return self.x

    @property
    def values(self):
        return self.y

    @property
    def depends_on_mapping(self):
        return self.numerator.source != self.denominator.source

    def __repr__(self):
        return f"ProxyRatio({self.name!r}, depends_on_mapping={self.depends_on_mapping})"

    def _white_sd(self, mask):
        # second differences over runs of three consecutive frames inside the mask
        x, y = self.x, self.y
        ok = mask & np.isfinite(y)
        i = np.arange(1, len(x) - 1)
        i = i[ok[i - 1] & ok[i] & ok[i + 1] & (x[i + 1] - x[i] == 1) & (x[i] - x[i - 1] == 1)]
        if len(i) < 3:
            return np.nan
        d2 = y[i + 1] - 2 * y[i] + y[i - 1]
        return d2.std() / np.sqrt(6)

    def deviation(self, core=None, scale="median"):
        """``(ratio - median over the core) / scale`` at all frames.

        ``scale="median"`` gives relative deviations; pass a number (e.g. 1.0) for ratios near 0.
        """
        mask = core_mask(self.x, core) & np.isfinite(self.y)
        if not mask.any():
            raise ValueError("no finite values in the core")
        med = np.median(self.y[mask])
        return (self.y - med) / _scale_of(med, scale)

    def flatness(self, core=None, scale="median"):
        """Descriptive flatness statistics over ``core`` (see :class:`Flatness`)."""
        mask = core_mask(self.x, core)
        fin = mask & np.isfinite(self.y)
        if fin.sum() < 4:
            raise ValueError("at least 4 finite points are needed in the core")
        x, y = self.x[fin].astype(float), self.y[fin]
        med = float(np.median(y))
        s = _scale_of(med, scale)
        noise_abs = self._white_sd(mask)
        slope, _ = np.polyfit(x, y, 1)
        sxx = ((x - x.mean()) ** 2).sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            sd_over_noise = y.std() / noise_abs
            tilt_z = slope * np.sqrt(sxx) / noise_abs
        tilt_quad = curvature = np.nan
        if len(x) >= 5:
            t = (x - x.mean()) / ((x[-1] - x[0]) / 2)
            c2, b, _ = np.polyfit(t, y, 2)
            tilt_quad, curvature = 2 * b / s, c2 / s
        return Flatness(n=int(fin.sum()), median=med, sd=float(y.std() / s), noise=float(noise_abs / s),
                        sd_over_noise=float(sd_over_noise), tilt=float(slope * (x[-1] - x[0]) / s),
                        tilt_z=float(tilt_z), tilt_quad=float(tilt_quad), curvature=float(curvature))


def independent_axes(ratios):
    """Number of independent axes of a set of ratios.

    Ratios of the same proxies are algebraically dependent (in log space
    ``log(A/I2) = log(I0/I2) - log(I0/A)``). A set of ratios is a graph whose nodes are
    the proxies and whose edges are the ratios; the number of independent axes is
    ``nodes - connected components``.

    Parameters
    ----------
    ratios : iterable
        :class:`ProxyRatio` objects or ``(numerator_name, denominator_name)`` tuples.
    """
    parent = {}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for r in ratios:
        if isinstance(r, ProxyRatio):
            a, b = r.numerator.name, r.denominator.name
        else:
            a, b = r
        parent.setdefault(a, a)
        parent.setdefault(b, b)
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    return len(parent) - len({find(a) for a in parent})
