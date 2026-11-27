"""
    LowRank.Findings.py

    What the rank-2 (interparticle) correction found, as data (molass-library#423): per finding a code, the library's own text (the text of the
    ``UserWarning``), a plain-language text without jargon, the part of the profile it affects, a suggested check, and the numbers behind it. The plain texts
    are the words a user of the GUI reads; the thresholds behind the findings are provisional (see ``SoftBoundedLrf``), so a finding is not a risk level.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Finding:
    """One thing about a rank-2 correction that deserves a look.

    Attributes
    ----------
    code : str
        ``'refine_at_bound'``, ``'k_small'``, ``'violation'``, ``'q_min_high'`` (soft-bounded LRF); ``'clipped_below_b1'``, ``'clipped_band'``, ``'l_penalized'``,
        ``'kl_negative'``, ``'q_min_high'`` (Bounded LRF).
    text : str
        The library's own text, the one of the ``UserWarning`` (technical).
    plain : str
        One or two sentences in plain language: what it means.
    region : str
        The part of the profile it affects.
    check : str
        A suggested check.
    values : dict
        The numbers behind it.
    """
    code: str
    text: str
    plain: str
    region: str
    check: str
    values: dict = field(default_factory=dict)

    def __str__(self):
        return f"[{self.code}] {self.plain} (affects: {self.region}; check: {self.check})"
