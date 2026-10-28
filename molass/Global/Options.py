"""
    Global.Options.py
"""

GLOBAL_OPTIONS = dict(
    mapped_trimming = True,
    anomaly_handling = True,
    flowchange = False,
    developer_mode = False,
    elution_recognition = 'icurve',
    quiet = False,
    small_angle_limit = 'extended',
)

def set_molass_options(**kwargs):
    """Set global options for molass.

    Parameters
    ----------
    mapped_trimming : bool, optional
        Whether to perform mapped trimming. Default is True.
        See :func:`molass.Trimming.TrimmingUtils.make_mapped_trimming_info` for details.
    anomaly_handling : bool, optional
        Whether trimming excludes an irregular end of the UV elution curve (a dip below the
        baseline in the last frames) from the trimming and from the XR/UV mapping. Default is True;
        data without such an anomaly is not affected. Set it to False to observe the anomaly itself
        (e.g. the tilted baseline in ``plot_compact(baseline=True)``, or the unstable mapping it
        causes). See :mod:`molass.Trimming.AnomalyHandler`.
    small_angle_limit : {'extended', 'guinier', 'none'}, optional
        How the trimming sets the start of the angular range (the lowest q kept), as in the legacy
        GUI's "Guinier Limit in Small Angle Data Trimming". Default is ``'extended'``: the extended
        limit beyond the Guinier range plus the B(q) limit, which keeps the low-q points where
        interparticle effects act. ``'guinier'`` is the minimum of the Guinier range (the default
        before molass-library#342; it can drop the lowest-q points of concentrated samples, e.g. 24
        of SAMPLE3's) and ``'none'`` keeps the whole measured range. It can also be given per call as
        ``trimmed_copy(small_angle_limit=...)`` or fixed by ``trimmed_copy(xr_qr=(start, stop))``.
    flowchange : bool or str, optional
        Whether to consider flow change. Default is False.
        If a string is given and equal to 'auto', flow change will be considered
        according to the beamline info of input data as follows.

        - If the beamline name starts with "PF", flow change will be considered.
        - Otherwise, flow change will not be considered.
    developer_mode : bool, optional
        Whether to enable developer mode. Default is False.
    elution_recognition : str, optional
        Which elution curve to use for peak detection and buffer-frame
        classification.  Default is ``'icurve'`` (single row at q≈0.02,
        current behaviour).  Set to ``'sum'`` to use the sum over all
        (trimmed) q-rows, which is more robust when baseline drift is
        q-dependent (e.g. MY-type datasets).
    quiet : bool, optional
        If True, suppress verbose diagnostic output from internal and
        legacy code during core API calls (``SSD()``, ``trimmed_copy()``,
        ``corrected_copy()``, ``quick_decomposition()``,
        ``optimize_rigorously()``).  Default is False.
    kwargs : dict
        Other options to set.
    """
    for key, value in kwargs.items():
        try:
            v = GLOBAL_OPTIONS[key]
        except:
            raise ValueError("No such global option: %s" % key)
        if key == 'small_angle_limit' and value not in ('extended', 'guinier', 'none'):
            raise ValueError("small_angle_limit must be 'extended', 'guinier' or 'none', not %r" % (value,))
        GLOBAL_OPTIONS[key] = value

def get_molass_options(*args):
    """Get global options for molass.

    Parameters
    ----------
    args : str
        The names of the options to get.
        The options are:

        - 'mapped_trimming': Whether to perform mapped trimming.
        - 'anomaly_handling': Whether to exclude an irregular UV end from trimming.
        - 'flowchange': Whether to consider flow change.
        - 'developer_mode': Whether to enable developer mode.
        - 'elution_recognition': Which elution curve to use for recognition
          (``'icurve'`` or ``'sum'``).
        - 'quiet': Whether to suppress verbose diagnostic output.
        - 'small_angle_limit': How trimming sets the lowest q kept
          (``'extended'``, ``'guinier'`` or ``'none'``).
    Returns
    -------
    dict
        The values of the requested options.
    """
    if len(args) == 1:
        return GLOBAL_OPTIONS[args[0]]
    else:
        return [GLOBAL_OPTIONS[key] for key in args]