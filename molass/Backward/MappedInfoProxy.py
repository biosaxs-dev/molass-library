"""
Backward.MappedInfoProxy.py
"""
from molass_legacy.Mapping.PeakMapper import MappedInfo

class MappedInfoProxy(MappedInfo):
    """
    A proxy class for MappedInfo, which is used to store information about the
    mapping of data.
    """
    def __init__(self, mapping):
        """
        Initialize the proxy with a MappedInfo object.
        """
        self._A, self._B = mapping.slope, mapping.intercept

def make_mapped_info(mapping):
    """
    Create a MappedInfoProxy from the given mapping.
    """
    return MappedInfoProxy(mapping)