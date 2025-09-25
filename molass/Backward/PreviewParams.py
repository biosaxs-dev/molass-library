"""
Backward.PreviewParams.py
"""

from molass_legacy.Extrapolation.PreviewData import PreviewData, PreviewOptions

class MapperProxy:
    """
    A proxy class for the mapper, which is used to determine if the mapper is for SEC.

    Attributes
    ----------
    x_curve : Curve
        The x-curve object.
    """
    def __init__(self, mapping):
        """
        Initialize the proxy with a MappingInfo object.

        Parameters
        ----------
        mapping : MappingInfo
            The MappingInfo object containing the mapping information.
        """
        self.x_curve = mapping.xr_curve

def make_preview_params(mapping, sd, paired_ranges):
    """
    Create preview parameters for the given inputs.

    Parameters
    ----------
    mapping : MappingInfo
        The MappingInfo object containing the mapping information.
    sd : SecSaxsData
        The SecSaxsData object containing the data.
    paired_ranges : list of tuples
        The paired ranges for the preview data.

    Returns
    -------
    (PreviewData, PreviewOptions)
    """
    mapper = MapperProxy(mapping)
    preview_data = PreviewData(sd=sd,
                               paired_ranges=paired_ranges,
                               mapper=mapper,
                               )
    preview_options = PreviewOptions()

    return preview_data, preview_options