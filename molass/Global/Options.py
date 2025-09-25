"""
    Global.Options.py
"""

GLOBAL_OPTIONS = dict(
    mapped_trimming = True,
    flowchange = False,
    uvdata = True,
    xrdata = True,
)

def set_molass_options(**kwargs):
    """Set global options for molass.
    Parameters
    ----------
    kwargs : dict
        Key-value pairs of options to set.
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
        
    Returns
    -------
    dict
        The values of the requested options.
    """
    if len(args) == 1:
        return GLOBAL_OPTIONS[args[0]]
    else:
        return [GLOBAL_OPTIONS[key] for key in args]