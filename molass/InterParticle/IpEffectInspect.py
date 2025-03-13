"""
    InterParticle.IpEffectInspect
"""
from importlib import reload

class IpEffectInfo:
    def __init__(self, scd):
        self.scd = scd

def inspect_ip_effect_impl(ssd, debug=False):
    if debug:
        import molass.InterParticle.ConcDepend
        reload(molass.InterParticle.ConcDepend)
    from molass.InterParticle.ConcDepend import compute_scd
    scd = compute_scd(ssd, debug=debug)
    return IpEffectInfo(scd)