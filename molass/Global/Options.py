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
    for key, value in kwargs.items():
        try:
            v = GLOBAL_OPTIONS[key]
        except:
            raise ValueError("No such global option: %s" % key)
        GLOBAL_OPTIONS[key] = value

def get_molass_options(*args):
    if len(args) == 1:
        return GLOBAL_OPTIONS[args[0]]
    else:
        return [GLOBAL_OPTIONS[key] for key in args]