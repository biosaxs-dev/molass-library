"""
    molass.Continuity

    Does a decomposition describe a few distinct species, or slices of a continuous
    distribution? Deterministic indicators and a cautious report (molass-library#370).
    Reached via ``Decomposition.get_continuity_report()``.
"""
from molass.Continuity.Indicators import (rg_point_noise, rg_drop, longest_constant_run, ramp_run_length,
                                          plateau_excess, find_plateaus, kratky_separation)
from molass.Continuity.Report import (ContinuityReport, compute_continuity_report, compute_continuity_report_of,
                                      DEFAULT_THRESHOLDS, VERDICT_DISCRETE, VERDICT_NO_EVIDENCE,
                                      VERDICT_UNDETERMINED)
