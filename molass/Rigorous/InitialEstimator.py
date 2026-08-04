"""
molass.Rigorous.InitialEstimator

Library-side equivalent of PeakEditor.draw_scores(): evaluates the rigorous
objective at initial parameters and returns the Score object.

Usage::

    est = InitialEstimator(decomposition, trimmed_ssd)
    score = est.evaluate()   # blocks; returns Score
    score.plot()

For the Tkinter progress-bar UI, see molass_gui.estimator_view.EstimatorView.

Copyright (c) 2026, SAXS Team, KEK-PF
"""
from __future__ import annotations


class InitialEstimator:

    def __init__(self, decomposition, trimmed_ssd=None):
        self.decomposition = decomposition
        self.trimmed_ssd = trimmed_ssd
        self._score = None

    # ------------------------------------------------------------------
    # Programmatic interface
    # ------------------------------------------------------------------

    def evaluate(self, progress_cb=None):
        """Compute and return the Score object."""
        self._score = self.decomposition.score(
            trimmed_ssd=self.trimmed_ssd,
            progress_cb=progress_cb,
        )
        return self._score

    @property
    def score(self):
        return self._score

    @property
    def optimizer(self):
        """Prepared legacy optimizer — ready for BH/DE after evaluate()."""
        return self._score.optimizer if self._score is not None else None

    # GUI interface lives in molass_gui.estimator_view (Tkinter-free policy).
