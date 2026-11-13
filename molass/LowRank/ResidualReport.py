"""
    LowRank.ResidualReport.py

    Residuals of a decomposition against the **measured** data and statistics on them (molass-library#392;
    molass-researcher experiment 58).

    ``Decomposition.get_xr_matrices()`` returns the rank-k denoised matrix, whose residual is white by
    construction. The residual computed here is that of the measured matrix ``M`` and the elution curves ``C`` of the
    decomposition, with ``P`` solved by least squares against ``M`` (frames above ``min_fraction`` of the strongest
    frame), in units of the stated error.

    Notes on the statistics (Rambo and Tainer 2025, Biophys. J. 124, 2511-2522):

    * Durbin-Watson (DW) is 2 for white residuals and does not depend on the scale of the errors: multiplying the
      stated error by 0.5 or 2 changes chi2 by a factor of 4 or 1/4 but leaves DW unchanged, so DW is usable where
      "chi2 reaches 1" is not (stated error wrong). DW along q of *measured* reduced data has a plateau of about
      1.8 at every rank (neighbouring q points are correlated), so compare it with that plateau, not with 2;
      DW along the elution is about 2 for a sufficient model.
    * Counting every q point as an independent datum favours k + 1 by hundreds of AIC units whatever the data
      (the oversampling paradox): the data are counted as ``Ns = qmax * dmax / pi`` independent values per profile
      (Shannon), and a profile costs ``Ns`` parameters.
    * Validated on simulated SAMPLE4 only (18 rigorous runs, experiment 58); not yet on real analyses.
"""
from dataclasses import dataclass
import numpy as np

PARAMS_PER_CURVE = 4        # elution-curve parameters of one component (EGH: H, mu, sigma, tau)
DMAX_PER_RG = 3.5           # rule of thumb for compact particles when no dmax is given


def durbin_watson(x):
    """Durbin-Watson statistic of a 1-D series: 2 for no lag-1 autocorrelation, below 2 for positive
    autocorrelation (structure left in the residual), above 2 for negative."""
    x = np.asarray(x, dtype=float)
    den = np.sum(x * x)
    return float(np.sum(np.diff(x) ** 2) / den) if den > 0 else float("nan")


def dw_columns(R):
    """Durbin-Watson statistic of every column of ``R`` (the series run along axis 0)."""
    den = np.sum(R * R, axis=0)
    return np.sum(np.diff(R, axis=0) ** 2, axis=0) / np.where(den > 0, den, np.nan)


def peak_frames(M, min_fraction=0.05):
    """Indices of the frames whose total intensity exceeds ``min_fraction`` of the strongest frame."""
    total = M.sum(axis=0)
    return np.flatnonzero(total > min_fraction * total.max())


def compute_residuals(decomposition, error_weighted=True, min_fraction=0.05):
    """The residual of the measured XR matrix and its frame indices; see :meth:`Decomposition.get_residuals`."""
    xr = decomposition.xr
    M = np.asarray(xr.M, dtype=float)
    C = np.asarray(decomposition.get_xr_matrices()[1], dtype=float)
    cols = peak_frames(M, min_fraction)
    P = np.linalg.lstsq(C[:, cols].T, M[:, cols].T, rcond=None)[0].T
    R = M - P @ C
    if error_weighted:
        if xr.E is None:
            raise ValueError("error_weighted=True needs the stated error, but the XR data have none")
        R = R / np.asarray(xr.E, dtype=float)
    return R, cols


@dataclass
class ResidualReport:
    """Statistics of the residual of a decomposition against the measured data.

    Attributes
    ----------
    num_components : int
    chi2 : float
        Mean squared residual in units of the stated error (about 1 for a sufficient model and a correct stated error).
    dw_q : float
        Durbin-Watson along q, averaged over the frames. About 2 for white residuals; measured reduced data have a
        plateau of about 1.8.
    dw_t : float
        Durbin-Watson along the elution, averaged over the q points (about 2 for a sufficient model).
    dw_q_frames, dw_t_q : numpy.ndarray
        Their per-frame and per-q-point values.
    num_frames : int
        Number of frames used (above ``min_fraction`` of the strongest frame).
    dmax, dmax_assumed : float, bool
        The maximum particle dimension in Angstrom used for the Shannon number, and whether it was estimated
        (``DMAX_PER_RG`` times the largest component Rg) instead of given.
    num_shannon : int
        ``Ns = ceil(qmax * dmax / pi)``, the number of independent values per profile.
    aic : float
        Shannon-limited AIC, ``Ns * num_frames * chi2 + 2 * k * (params_per_curve + Ns)``. Only differences between
        decompositions of the same data are meaningful (:meth:`delta_aic`); negative: the second one is preferred.
    aic_all_points : float
        The same with every q point counted as independent datum (``n_q`` instead of ``Ns``), for contrast only.
    """
    num_components: int
    chi2: float
    dw_q: float
    dw_t: float
    dw_q_frames: np.ndarray
    dw_t_q: np.ndarray
    num_frames: int
    num_q: int
    dmax: float
    dmax_assumed: bool
    num_shannon: int
    params_per_curve: int
    aic: float
    aic_all_points: float

    def delta_aic(self, other, all_points=False):
        """``other.aic - self.aic``: positive when ``self`` (the smaller model, say) is preferred over ``other``.

        Both reports must come from the same data and the same ``dmax``. ``all_points=True`` gives the
        oversampled version (shown only to demonstrate the paradox)."""
        if all_points:
            return other.aic_all_points - self.aic_all_points
        if self.dmax != other.dmax or self.num_frames != other.num_frames:
            raise ValueError("the reports must use the same dmax and the same frames; pass the same dmax= to both")
        return other.aic - self.aic

    def __repr__(self):
        dmax = f"{self.dmax:.0f}" + (" (assumed)" if self.dmax_assumed else "")
        return (f"ResidualReport(k={self.num_components}, chi2={self.chi2:.3f}, DW along q={self.dw_q:.2f}, "
                f"DW along the elution={self.dw_t:.2f}, Shannon AIC={self.aic:.1f} (dmax {dmax}, Ns {self.num_shannon}), "
                f"frames={self.num_frames})")


def compute_residual_report(decomposition, dmax=None, min_fraction=0.05, params_per_curve=PARAMS_PER_CURVE):
    """See :meth:`Decomposition.get_residual_report`."""
    Z, cols = compute_residuals(decomposition, error_weighted=True, min_fraction=min_fraction)
    Z = Z[:, cols]
    dw_frames = dw_columns(Z)
    dw_q_points = dw_columns(Z.T)
    chi2 = float(np.mean(Z ** 2))
    k = decomposition.num_components
    n_q, n_frames = Z.shape
    xr = decomposition.xr
    dmax_assumed = dmax is None
    if dmax_assumed:
        rgs = [c.compute_rg() for c in decomposition.get_xr_components()]
        rgs = [float(r) for r in rgs if r is not None and np.isfinite(r)]
        if not rgs:
            raise ValueError("dmax was not given and no component has a Guinier Rg to estimate it from")
        dmax = DMAX_PER_RG * max(rgs)
    qmax = float(np.max(xr.qv))
    ns = int(np.ceil(qmax * dmax / np.pi))
    penalty = 2 * k * (params_per_curve + ns)
    return ResidualReport(
        num_components=k, chi2=chi2, dw_q=float(np.nanmean(dw_frames)), dw_t=float(np.nanmean(dw_q_points)),
        dw_q_frames=dw_frames, dw_t_q=dw_q_points, num_frames=n_frames, num_q=n_q,
        dmax=float(dmax), dmax_assumed=dmax_assumed, num_shannon=ns, params_per_curve=params_per_curve,
        aic=ns * n_frames * chi2 + penalty,
        aic_all_points=n_q * n_frames * chi2 + 2 * k * (params_per_curve + n_q))
