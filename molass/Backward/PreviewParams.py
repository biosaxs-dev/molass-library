"""
Backward.PreviewParams.py
"""

from molass_legacy.Extrapolation.PreviewData import PreviewData, PreviewOptions

class MapperProxy:
    """
    A proxy class for the mapper, which is used to determine if the mapper is for SEC.
    """
    def __init__(self, mapping):
        self.x_curve = mapping.xr_curve

def make_preview_params(mapping, sd, paired_ranges):
    """
    Create preview parameters for the given inputs.
    """

    mapper = MapperProxy(mapping)
    preview_data = PreviewData(sd=sd,
                               paired_ranges=paired_ranges,
                               mapper=mapper,
                               )
    preview_options = PreviewOptions()

    return preview_data, preview_options