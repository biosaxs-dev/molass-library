"""
Backward.MappedInfoProxy.py
"""
from molass_legacy.Mapping.PeakMapper import MappedInfo

XR_METHOD_MAP = {'linear': 1, 'integral': 5}
UV_METHOD_MAP = {'linear': 1, 'uvdiff': 4, 'integral': 5}

def methood_to_legacy_opts(method):
    """
    Convert a method string to legacy options.
    """
    if type(method) is str:
        methods = (method, method)
    else:
        methods = method
    return XR_METHOD_MAP.get(methods[0], 1), UV_METHOD_MAP.get(methods[1], 1)

class MappedInfoProxy(MappedInfo):
    """
    A proxy class for MappedInfo, which is used to store information about the
    mapping of data.
    """
    def __init__(self, ssd, mapping):
        """
        Initialize the proxy with a MappedInfo object.
        """
        self._A, self._B = mapping.slope, mapping.intercept
        from molass_legacy._MOLASS.SerialSettings import set_setting
        from molass_legacy.Mapping.MappingParams import get_mapper_opt_params
        """
        task: consistent set_setting() calls are required
        """
        method = ssd.get_baseline_method()  # ensure baseline method is set
        xr_opt, uv_opt = methood_to_legacy_opts(method)
        set_setting('use_xray_conc', False)
        set_setting('xray_baseline_opt', xr_opt)
        set_setting('uv_baseline_opt', uv_opt)
        self.opt_params = get_mapper_opt_params()

def make_mapped_info(ssd, mapping):
    """
    Create a MappedInfoProxy from the given mapping.
    """
    return MappedInfoProxy(ssd, mapping)