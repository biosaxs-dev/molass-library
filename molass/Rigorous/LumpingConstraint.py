"""
molass.Rigorous.LumpingConstraint
=================================

Prevents component peak drift across group boundaries during rigorous
optimization (the "lumping" problem).

Usage::

    from molass.Rigorous import LumpingConstraint

    constraint = LumpingConstraint(decomp)
    run = decomp_sdm.optimize_rigorously(
        method='DE', niter=100,
        analysis_folder='temp_analysis',
        constraints=[constraint],
    )

The constraint is injected into ``BasicOptimizer._constraints`` before
``solve()`` is called (in-process path only).  It adds a soft-ramp penalty
proportional to the distance a component's peak has crossed into the wrong
group's territory, using escape-zone boundaries so that the leftmost and
rightmost components are also bounded.

Algorithm
---------
1. K-means clusters the initial peak positions into *n_groups* groups, where
   ``n_groups = len(decomp.xr_icurve.get_peaks())``.
2. Natural group boundaries are midpoints between sorted K-means centroids.
3. Escape-zone boundaries extend ``escape_margin`` frames beyond the outermost
   peaks — ensuring all components have a bounded region (no open-ended group).
4. Reference labels are assigned from this extended boundary set; real
   components get labels ≥ 1 (groups 0 and *n_groups+1* are escape zones).
5. At each objective call, each component's current peak position is
   checked; the penalty is ``weight × Σ penetration_distance``, where
   penetration is the number of frames past the nearest violated boundary.
"""

import numpy as np

__all__ = ['LumpingConstraint']

# Default soft-ramp weight: 0.2 fv per elution frame of penetration.
# Calibrated so a full 25-frame crossing costs ~5 fv units — comparable to
# the hard-step penalty of +10 for 2 simultaneously violating components.
DEFAULT_WEIGHT = 0.2


def _get_peak_positions(xr_cy_list, x, n_comp):
    """Return peak-top frame positions for the first *n_comp* components."""
    return [float(x[np.argmax(cy)]) for cy in xr_cy_list[:n_comp]]


def _penetration(pos, label, boundaries):
    """Frames past the constraint boundary. 0 if the component is inside."""
    if label == 0:
        # left escape zone — component must stay left of boundaries[0]
        return max(0.0, pos - boundaries[0])
    elif label == len(boundaries):
        # right escape zone — component must stay right of boundaries[-1]
        return max(0.0, boundaries[-1] - pos)
    else:
        left_viol  = max(0.0, boundaries[label - 1] - pos)
        right_viol = max(0.0, pos - boundaries[label])
        return max(left_viol, right_viol)


def _compute_boundaries(decomp, n_groups=None, escape_margin=None):
    """Compute escape-zone boundaries and reference labels.

    Parameters
    ----------
    decomp : Decomposition
        Initial decomposition from which to derive peak positions.
    n_groups : int or None
        Number of component groups.  Defaults to
        ``len(decomp.xr_icurve.get_peaks())``.
    escape_margin : float or None
        Frames to extend beyond outermost peak positions for escape zones.
        Defaults to half the mean centroid spacing.

    Returns
    -------
    ref_labels : list of int
        Group index (≥ 1) for each component.
    boundaries : numpy.ndarray
        ``[left_escape, *natural_boundaries, right_escape]``.
    """
    from sklearn.cluster import KMeans

    peak_positions = [float(cc.x[np.argmax(cc.y)]) for cc in decomp.xr_ccurves]
    if n_groups is None:
        n_groups = len(decomp.xr_icurve.get_peaks())

    km = KMeans(n_clusters=n_groups, random_state=0, n_init='auto')
    km.fit(np.array(peak_positions).reshape(-1, 1))
    sorted_centroids = np.sort(km.cluster_centers_[:, 0])
    natural_boundaries = (sorted_centroids[:-1] + sorted_centroids[1:]) / 2

    if escape_margin is None:
        escape_margin = float(np.mean(np.diff(sorted_centroids)) / 2)

    left_escape  = min(peak_positions) - escape_margin
    right_escape = max(peak_positions) + escape_margin
    boundaries = np.concatenate([[left_escape], natural_boundaries, [right_escape]])

    ref_labels = [int(np.searchsorted(boundaries, pos)) for pos in peak_positions]
    return ref_labels, boundaries


class LumpingConstraint:
    """Soft-ramp lumping constraint with escape zones.

    Prevents component peaks from drifting across group boundaries during
    rigorous optimization.  Designed for multi-component datasets where the
    default DE optimizer may collapse components without a constraint.

    Parameters
    ----------
    decomp : Decomposition
        The initial decomposition.  Used to determine reference peak
        positions and group boundaries via K-means.
    n_groups : int or None
        Number of component groups.  Default: auto-detected from
        ``decomp.xr_icurve.get_peaks()``.
    escape_margin : float or None
        Extra frames beyond the outermost peaks for escape zones.
        Default: half the mean inter-centroid spacing.
    weight : float
        Penalty per elution frame of boundary penetration.  Default 0.2.

    Examples
    --------
    >>> constraint = LumpingConstraint(decomp)
    >>> run = decomp_sdm.optimize_rigorously(
    ...     method='DE', niter=100,
    ...     analysis_folder='temp_analysis',
    ...     constraints=[constraint],
    ... )
    """

    def __init__(self, decomp, n_groups=None, escape_margin=None,
                 weight=DEFAULT_WEIGHT):
        self.weight = weight
        self.ref_labels, self.boundaries = _compute_boundaries(
            decomp, n_groups=n_groups, escape_margin=escape_margin)
        self._n_comp = len(self.ref_labels)

    def __call__(self, lrf_info):
        """Return the constraint penalty for the current optimizer state.

        Parameters
        ----------
        lrf_info : object
            The ``lrf_info`` object passed through ``BasicOptimizer.compute_fv``.
            Must expose ``get_xr_cy_list()`` and ``x``.

        Returns
        -------
        float
            Total penetration penalty (≥ 0).
        """
        xr_cy_list = lrf_info.get_xr_cy_list()
        x = lrf_info.x
        positions = _get_peak_positions(xr_cy_list, x, self._n_comp)
        pen = sum(
            _penetration(pos, label, self.boundaries)
            for pos, label in zip(positions, self.ref_labels)
        )
        return self.weight * pen

    def __repr__(self):
        return (
            f"LumpingConstraint(n_comp={self._n_comp}, "
            f"ref_labels={self.ref_labels}, "
            f"weight={self.weight}, "
            f"boundaries={[f'{b:.1f}' for b in self.boundaries]})"
        )
