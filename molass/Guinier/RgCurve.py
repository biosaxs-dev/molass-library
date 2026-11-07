"""
    Guinier.RgCurve.py

    This module contains the class RgCurve, which is used to store Rg curve information.
"""
import numpy as np
from molass.DataObjects.Curve import Curve

class RgCurve(Curve):
    """
    A class to represent an Rg curve.

    See :doc:`the after-analysis cookbook </after_analysis>` for
    examples comparing data and model-reconstructed Rg curves.

    Attributes
    ----------
    indeces : np.ndarray
        The indices of the frames used to compute the Rg values.
    rgvalues : np.ndarray
        The Rg values corresponding to the indeces.
    scores : np.ndarray
        The estimator's raw quality scores for each frame. SimpleGuinier
        scores are weighted interval-fit scores in [0, 1]; ATSAS Autorg
        ``Quality`` values are a different weighted composite in [0, 1].
        A score of 0.6 is a heuristic threshold, not a confidence probability,
        and the two estimators' scores are not interchangeable.
    results : list or None
        The results of the Rg computation. It can be None if not specified.
    intensities : list or None
        The intensities corresponding to the indeces. It can be None if not specified.

    """

    def __init__(self, indeces, rgvalues, scores, results=None, intensities=None, score_source=None):
        """
        """
        indeces = np.asarray(indeces, dtype=int)
        super().__init__(indeces, rgvalues, type='i')
        assert len(indeces) == len(rgvalues) == len(scores)
        self.index_dict = {}
        for k, i in enumerate(indeces):
            self.index_dict[i] = k
        self.indeces = indeces
        self.rgvalues = rgvalues
        self.scores = scores
        self.results = results  # either, molass results or atsas results
        self.intensities = intensities  # only for molass results, None for atsas results
        self.score_source = score_source

    @property
    def frames(self):
        """Frame numbers (alias for ``indeces``). These are actual frame
        numbers, not positional array indices."""
        return self.indeces

    @property
    def rgs(self):
        """Rg values in Angstrom (alias for ``rgvalues``); NaN where the Guinier fit failed.
        ``get_xy()`` returns the same data as ``(frames, rgs)``."""
        return self.rgvalues

    def _result_values(self, name):
        n = len(self.indeces)
        if self.results is None:
            return np.full(n, np.nan)
        values = np.full(n, np.nan)
        for k, r in enumerate(self.results):
            v = None if r is None else getattr(r, name, None)
            if v is not None:
                values[k] = v
        return values

    @property
    def i0s(self):
        """I(0) of the per-frame Guinier fits, in the units of the intensities
        (same length and order as ``frames``); NaN where the fit failed."""
        return self._result_values('I0')

    @property
    def has_i0(self):
        """Whether any I(0) is available. An Rg curve restored from disk (``try_fast_rg_curve``)
        carries Rg and scores but no I(0)."""
        return bool(np.isfinite(self.i0s).any())

    @property
    def i0_errors(self):
        """Standard deviation of ``i0s``; NaN where not available
        (failed fit, or results that carry no I(0) error, e.g. ATSAS)."""
        return self._result_values('I0_stdev')

    def reliable(self, score_min=0.6, intensity=None, intensity_frac=0.05):
        """Return frames and Rg values passing the standard reliability filters.

        A result is usable when its score is at least ``score_min``, its Rg is
        finite and in ``(0, 99)`` (excluding failed fits and the 100 Å
        sentinel), and, when provided, its aligned intensity is finite and at
        least ``intensity_frac`` of the maximum. ``intensity`` must have one
        value per entry in :attr:`frames`.

        ``score_min=0.6`` retains frames whose SimpleGuinier interval-fit
        score is at least 0.6, or whose ATSAS Autorg weighted-composite
        ``Quality`` is at least 0.6. Both are normalized to [0, 1], but use
        different factors; 0.6 is not a probability and does not imply
        identical fit quality between the estimators.
        """
        if not np.isfinite(score_min) or not 0 <= score_min <= 1:
            raise ValueError("score_min must be finite and between 0 and 1")
        if not np.isfinite(intensity_frac) or not 0 <= intensity_frac <= 1:
            raise ValueError("intensity_frac must be finite and between 0 and 1")
        rgs = np.asarray(self.rgvalues, dtype=float)
        scores = np.asarray(self.scores, dtype=float)
        mask = np.isfinite(rgs) & (rgs > 0) & (rgs < 99) & np.isfinite(scores) & (scores >= score_min)
        if intensity is not None:
            intensities = np.asarray(intensity, dtype=float)
            if intensities.ndim != 1 or len(intensities) != len(self.frames):
                raise ValueError("intensity must be a 1D array aligned with frames")
            finite = np.isfinite(intensities)
            if finite.any():
                threshold = intensity_frac * np.max(intensities[finite])
                mask &= finite & (intensities >= threshold)
            else:
                mask[:] = False
        return self.frames[mask], rgs[mask]

    def noise(self, score_min=0.6, intensity=None, intensity_frac=0.05):
        """Standard deviation of a single-frame Rg value (Å) of the reliable frames.

        A robust estimate from the differences of neighbouring frames (see
        :func:`molass.Continuity.Indicators.rg_point_noise`); the frames are those of
        :meth:`reliable` with the same arguments. It is what the total Rg drop is compared with
        in the continuity report. NaN with fewer than two usable pairs of consecutive frames.
        """
        from molass.Continuity.Indicators import rg_point_noise
        frames, rgs = self._reliable_sorted(score_min, intensity, intensity_frac)
        return rg_point_noise(frames, rgs) if len(rgs) >= 2 else float('nan')

    def drop(self, score_min=0.6, intensity=None, intensity_frac=0.05):
        """Total drop of the Rg of the reliable frames (Å): ``|median of the first five - median of
        the last five|`` (see :func:`molass.Continuity.Indicators.rg_drop`). NaN without reliable frames."""
        from molass.Continuity.Indicators import rg_drop
        _, rgs = self._reliable_sorted(score_min, intensity, intensity_frac)
        return rg_drop(rgs) if len(rgs) else float('nan')

    def _reliable_sorted(self, score_min, intensity, intensity_frac):
        frames, rgs = self.reliable(score_min=score_min, intensity=intensity, intensity_frac=intensity_frac)
        order = np.argsort(frames)
        return frames[order], rgs[order]

    def __repr__(self):
        """Summarize frame coverage, Rg/I(0) availability and known score source.

        An Rg curve restored from disk (``try_fast_rg_curve``) can cover only part of the frames
        and carry no I(0); the representation makes that visible (molass-library#332). When known,
        the score source is also shown because SimpleGuinier and ATSAS quality scores differ (#361).
        """
        n = len(self.indeces)
        if n == 0:
            return "RgCurve(empty)"
        first, last = int(np.min(self.indeces)), int(np.max(self.indeces))
        n_rg = int(np.isfinite(np.asarray(self.rgvalues, dtype=float)).sum())
        n_i0 = int(np.isfinite(self.i0s).sum())
        parts = [f"{n} frames {first}-{last}"]
        n_missing = (last - first + 1) - n
        if n_missing > 0:
            parts.append(f"{n_missing} frames missing in between")
        parts.append(f"finite Rg: {n_rg}")
        parts.append(f"I(0): {n_i0} finite" if n_i0 > 0 else "I(0): not available")
        if self.score_source is not None:
            parts.append(f"scores: {self.score_source}")
        return "RgCurve(" + ", ".join(parts) + ")"


def construct_rgcurve_from_list(rginfo_list, result_type=None):
    """
    Constructs an RgCurve from a result list.

    Parameters
    ----------
    rginfo_list : list of tuples
        A list of tuples where each tuple contains (index, result).
        The result can be either a SimpleGuinier result or an ATSAS Autorg result.
    result_type : str or None
        If None, the results are assumed to be SimpleGuinier results.
        If 'atsas', the results are assumed to be ATSAS Autorg results.
        Default is None.

    Returns
    -------
    RgCurve
        An RgCurve object constructed from the provided result list.
    """
    from molass_legacy.GuinierAnalyzer.AutorgKekAdapter import AutorgKekAdapter
    indeces = []
    values = []
    scores = []
    results = []
    intensities = [] if result_type is None else None
    score_source = ("SimpleGuinier interval-fit score (0-1)" if result_type is None
                    else "ATSAS Autorg Quality (0-1)")
    for k, (i, result) in enumerate(rginfo_list):
        indeces.append(i)
        rg = result.Rg
        values.append(rg if (rg is not None and rg > 0) else float('nan'))
        if result_type is None:
            # SimpleGuinier result
            scores.append(result.score)
            adapter = AutorgKekAdapter(None, guinier=result)
            intensities.append(adapter.intensity)
            result_ = adapter.run(robust=True, optimize=True)
        else:
            # ATSAS.AutorgRunner result
            scores.append(result.Quality)
            result_ = result
        results.append(result_)
    
    return RgCurve(np.array(indeces), np.array(values, dtype=float), np.array(scores), results=results,
                    intensities=intensities, score_source=score_source)
