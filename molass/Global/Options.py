"""
    Global.Options.py
"""

GLOBAL_OPTIONS = dict(
    mapped_trimming = True,
    flowchange = False,
    developer_mode = False,
)

def set_molass_options(mapped_trimming=True, flowchange=False, deveoloper_mode=False, **kwargs):
    """Set global options for molass.

    Parameters
    ----------
    mapped_trimming : bool, optional
        Whether to perform mapped trimming. Default is True.
        See :func:`molass.Trimming.TrimmingUtils.make_mapped_trimming_info` for details.
    flowchange : bool or str, optional
        Whether to consider flow change. Default is False.
        If a string is given and equal to 'auto', flow change will be considered
        according to the beamline info of input data as follows.

        - If the beamline name starts with "PF", flow change will be considered.
        - Otherwise, flow change will not be considered.
    developer_mode : bool, optional
        Whether to enable developer mode. Default is False.
    kwargs : dict
        Other options to set.
    """
    for key, value in kwargs.items():
        try:
            v = GLOBAL_OPTIONS[key]
        except:
            raise ValueError("No such global option: %s" % key)
        GLOBAL_OPTIONS[key] = value

def get_molass_options(*args):
    """Get global options for molass.

    Parameters
    ----------
    args : str
        The names of the options to get.
        The options are:

        - 'mapped_trimming': Whether to perform mapped trimming.
        - 'flowchange': Whether to consider flow change.
        - 'developer_mode': Whether to enable developer mode.
    Returns
    -------
    dict
        The values of the requested options.
    """
    if len(args) == 1:
        return GLOBAL_OPTIONS[args[0]]
    else:
        return [GLOBAL_OPTIONS[key] for key in args]