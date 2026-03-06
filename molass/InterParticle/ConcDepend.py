"""
    InterParticle.ConcDepend.py

    Note: This module is a placeholder. The full SCD computation is implemented in
    molass_legacy.Conc.ConcDepend (in the molass-legacy package).
    That implementation fits a quadratic model I(q,c) ≈ cA(q) + c²B(q) against
    the concentration series and returns a score quantifying interparticle interference.
    See also molass.Backward.RankEstimator for how SCD drives rank auto-detection.
"""

def compute_scd(ssd, debug=False):
    """ Compute the SCD (Score of Concentration Dependency) from the SampledScatteringData (SSD) object.

    Currently a placeholder that returns 0.
    The real implementation lives in ``molass_legacy.Conc.ConcDepend``.

    Parameters
    ----------
    ssd : SampledScatteringData
        The sampled scattering data containing XR data and inter-particle effect information.
    debug : bool
        If True, print debug information.
        
    Returns
    -------
    float
        The computed SCD.
    """
    return 0