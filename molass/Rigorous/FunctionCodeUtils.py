"""
Rigorous.FunctionCodeUtils

Shared helper for auto-detecting the legacy objective function code
from a Decomposition's model type and column parameters.

This avoids duplicating the detection logic in RigorousImplement.py
(launch path) and CurrentStateUtils.py (load path).
See: https://github.com/biosaxs-dev/molass-library/issues/89
"""

# Map (pore_dist, rt_dist) → legacy objective function code.
FUNCTION_CODE_MAP = {
    ('mono', 'exponential'): 'G1100',    # classic SDM
    ('mono', 'gamma'):       'G1200',    # SDM-Gamma
    # ('lognormal', 'gamma'):  'G1300',  # future: SDM-Lognormal-Gamma
}


def detect_function_code(decomposition):
    """Auto-detect the legacy objective function code.

    Uses the ``pore_dist`` and ``rt_dist`` attributes on the
    decomposition's ``SdmColumn`` to look up the appropriate
    legacy objective function class.

    Parameters
    ----------
    decomposition : Decomposition
        A quick decomposition whose ``xr_ccurves[0]`` carries the
        model type and (for SDM) the column parameters.

    Returns
    -------
    str or None
        A function code string (e.g. ``'G1200'``), or ``None``
        to use the default for the model.
    """
    ccurve = decomposition.xr_ccurves[0]
    if ccurve.model != "sdm":
        return None
    column = ccurve.column
    key = (getattr(column, 'pore_dist', 'mono'),
           getattr(column, 'rt_dist', 'gamma'))
    return FUNCTION_CODE_MAP.get(key)
