"""
Backward.PreviewParams.py
"""

from molass_legacy.Extrapolation.PreviewData import PreviewData, PreviewOptions

def make_preview_params(sd=None, paired_ranges=None):
    """
    Create preview parameters for the given inputs.
    """
    preview_data = PreviewData(sd=sd,
                               paired_ranges=paired_ranges,
                               mapper='not None',   # for is_for_sec to be True
                               )
    preview_options = PreviewOptions()

    return preview_data, preview_options