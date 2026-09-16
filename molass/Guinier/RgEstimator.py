"""
Guinier.RgEstimator.py
"""
import logging
import numpy as np
from scipy.stats import linregress
from molass_legacy.GuinierAnalyzer.SimpleGuinier import SimpleGuinier
from .SimpleFallback import SimpleFallback

logger = logging.getLogger(__name__)

# widened qRg tolerance for the in-place legacy retry (see molass-researcher
# experiments/38_guinier_analysis/38b-38d); large enough to admit the large-particle
# frames rejected by the strict 1.3 default, without being validated further here.
_RELAXED_QRG_LIMIT = 1.8
# DENSS-quality-confidence cap: this path never validates qRg<1.3 at all, so even
# a perfect linear fit shouldn't be scored as high as a fully-validated legacy fit
# (see molass-researcher experiments/38_guinier_analysis/38b, 38c).
_DENSS_SCORE_CAP = 0.5
# fallback (heuristic, clipped) confidence cap -- lower still, since this is the
# last-resort path; a saturated (clipped) value carries no real magnitude
# information at all and is scored 0.
_FALLBACK_SCORE_CAP = 0.2

def _guinier_fit_with_quality(data, ne):
    """Same window-shifting logic as DENSS's ``calc_rg_I0_by_guinier``, reimplemented
    locally (rather than calling it) so the fit's r_value is available to derive a
    meaningful ``score`` -- ``calc_rg_I0_by_guinier`` itself only returns (Rg, I0)."""
    nb = 0
    while True:
        # buffer-region frames routinely have non-positive intensities in this
        # window -- np.log(negative/zero) is an expected step towards the
        # ValueError below, not a real problem; silence the RuntimeWarning noise.
        with np.errstate(invalid='ignore', divide='ignore'):
            slope, intercept, r_value, p_value, stderr = linregress(
                data[nb:ne, 0] ** 2, np.log(data[nb:ne, 1]))
        if slope < 0:
            break
        nb += 1
        ne += 1
        if nb > 50:
            raise ValueError("Guinier estimation failed. Guinier region slope is positive.")
    rg = (-3 * slope) ** 0.5
    I0 = np.exp(intercept)
    return rg, I0, r_value, nb, ne

class RgEstimator(SimpleGuinier):
    """
    Rg estimator with a graceful fallback chain when the legacy Guinier
    analyzer fails to find a qRg-valid linear region (``Rg is None or 0``), or
    "succeeds" with a score of exactly 0 -- a coincidental fit on pure noise
    (see molass-researcher experiments/38_guinier_analysis/38c: a buffer-region
    frame with no real particle signal can still pass `SimpleGuinier`'s qRg
    check by chance, giving a confident-looking but meaningless ``Rg``):

    1. ``SimpleGuinier`` (legacy, strict qRg<1.3 validity check) -- tried first.
    2. A relaxed, in-place retry of the same legacy fit: widen the qRg limit to
       ``_RELAXED_QRG_LIMIT`` *and* pass ``max_candidates=None`` to disable
       `guinier_interval`'s per-`start` candidate-count throttle (molass-legacy
       issue #100), so a shorter, better-scoring window isn't skipped just
       because a longer one at the same `start` was found first. Accepted only
       if it also clears both failure checks. See molass-researcher
       experiments/38_guinier_analysis/38d: validated on a full 1233-frame
       dataset -- 5/7 recovered frames improved to a more physically plausible
       Rg (consistent with an independently-decomposed component's Rg), 2/7
       unchanged, zero frames outside the narrow retry trigger were affected,
       and known spurious noise fits remained correctly flagged.
    3. DENSS's ``calc_rg_I0_by_guinier`` (already vendored in molass-library,
       no qRg check) -- tried only if step 2 didn't clear both checks either.
       See molass-researcher experiments/38_guinier_analysis/38b, 38c.
    4. ``SimpleFallback`` (heuristic sliding-window fit, clipped to
       ``[MIN_RG, MAX_RG]``) -- last resort.

    Attributes
    ----------
    rg_source : str
        Which estimator produced ``Rg``: ``'legacy'``, ``'legacy_relaxed'``,
        ``'denss'``, or ``'fallback'``.
    saturated : bool
        True only when ``rg_source == 'fallback'`` and the returned Rg sits
        exactly at ``SimpleFallback``'s ``MIN_RG``/``MAX_RG`` clip boundary --
        i.e. the value is a saturation artifact, not a real fit result.

    Notes
    -----
    ``score`` is always populated, even when ``rg_source != 'legacy'`` (previously
    it silently stayed at the legacy fit's failure value of 0, making a recovered,
    physically plausible Rg indistinguishable from a total failure to any code that
    weights/filters by score -- e.g. ``plot_compact``'s Rg overlay opacity or
    ``GuinierDeviation``'s quality masking). It is capped well below a fully
    validated legacy score (``_DENSS_SCORE_CAP``, ``_FALLBACK_SCORE_CAP``) to
    reflect the lower confidence of these paths.
    """
    def __init__(self, data):
        super().__init__(data)
        self.rg_source = 'legacy'
        self.saturated = False
        # score==0 with Rg>0 is rare (4/1225 real frames in the 38c dataset) and
        # marks a coincidental fit with no real linearity signal at all -- distinct
        # from an ordinary low-but-nonzero score, which is left untouched here.
        if self.Rg is None or self.Rg == 0 or self.score == 0:
            if not self._try_relaxed_legacy():
                if not self._try_denss_guinier(data):
                    self._try_fallback(data)
        # SimpleGuinier's own null-result path (too few points, or an exception
        # during quality evaluation) never assigns guinier_start/guinier_stop at
        # all -- if every fallback above also failed to set them, plotting code
        # that reads these attributes would hit a bare AttributeError instead of
        # a checkable None (molass-library issue #269).
        if not hasattr(self, 'guinier_start'):
            self.guinier_start = None
        if not hasattr(self, 'guinier_stop'):
            self.guinier_stop = None

    def _try_relaxed_legacy(self):
        # guinier_interval()/make_cadidate_pairs() read self.worst_quality, which is
        # only ever set inside evaluate_basic_quality(). That method is skipped
        # entirely when SimpleGuinier.__init__ takes its set_guinier_null_result()
        # branch (too little data) -- and that branch also resets basic_quality to
        # 0, so checking "basic_quality is None" here does NOT reliably detect this
        # case. Check the actual attribute the retry depends on instead.
        if not hasattr(self, 'worst_quality'):
            return False
        try:
            self.guinier_interval(qrg_limit=_RELAXED_QRG_LIMIT, max_candidates=None)
            if self.Rg is None or self.Rg == 0 or self.score == 0:
                return False
            self.rg_source = 'legacy_relaxed'
            return True
        except Exception:
            # expected/common on buffer-region frames (no real particle signal) --
            # debug, not warning, so default logging stays quiet; still traceable
            # with exc_info=True when DEBUG is enabled.
            logger.debug("Relaxed legacy Guinier retry failed.", exc_info=True)
            return False

    def _try_denss_guinier(self, data):
        try:
            ne = min(20, data.shape[0])
            rg, I0, r_value, nb, ne = _guinier_fit_with_quality(data, ne)
            if rg is None or not np.isfinite(rg) or rg <= 0:
                return False
            self.Rg = rg
            self.Iz = I0
            self.guinier_start = nb
            self.guinier_stop = ne
            self.min_q = data[nb, 0]
            self.max_q = data[ne - 1, 0]
            self.rg_source = 'denss'
            self.score = min(_DENSS_SCORE_CAP, r_value ** 2)
            return True
        except Exception:
            logger.debug("DENSS Guinier fallback failed.", exc_info=True)
            return False

    def _try_fallback(self, data):
        try:
            fallback = SimpleFallback(data)
            result = fallback.estimate()
            self.Rg = result['Rg']
            self.Iz = result['I0']
            self.guinier_start = result['q_start']
            self.guinier_stop = result['q_stop']
            self.min_q = result['q_min']
            self.max_q = result['q_max']
            self.rg_source = 'fallback'
            self.saturated = bool(result.get('saturated', False))
            r_squared = result.get('r_squared', 0.0)
            self.score = 0.0 if self.saturated else min(_FALLBACK_SCORE_CAP, r_squared)
        except Exception:
            logger.debug("Fallback Rg estimation failed.", exc_info=True)