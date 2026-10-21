"""
    SAXS.DenssResult.py

    Reader for the per-component result files written by the DENSS runs of MOLASS:

        <denss_folder>/component_N/component_N_fitdata.fit   (parameters + fitted curve)
        <denss_folder>/component_N/component_N_map.fit      (data q, I, error and I of the density)

    Light module (numpy only), separate from ``DenssUtils`` which imports the DENSS core.
"""
import os
import re
import numpy as np


class DenssFit:
    """Result of one DENSS run, read back from its ``*_fitdata.fit`` / ``*_map.fit`` files.

    Attributes
    ----------
    folder, prefix : str
    params : dict
        Header values of ``*_fitdata.fit`` as floats, with ``I(0)`` renamed ``I0``
        (``Dmax``, ``alpha``, ``Rg``, ``I0``, ``Vp``, ... ; NaN where the file says nan),
        plus ``chi2`` of the density fit when ``*_map.fit`` exists. ``<key>_err`` holds the
        ``+-`` uncertainty where given.
    q_fit, I_fit : ndarray
        The smooth fitted curve of ``*_fitdata.fit`` (extrapolated to q = 0).
    q, I, error : ndarray or None
        The data points from ``*_map.fit`` (None if that file is missing).
    I_density : ndarray or None
        Intensity computed from the final density at ``q`` (None if no ``*_map.fit``).
    Rg, Iz : float
        ``params["Rg"]`` and ``params["I0"]``; with these two a ``DenssFit`` can stand in for the
        Guinier object that :func:`molass.Kratky.ShapeMatch.compute_shape_match_scores` expects.
    """

    def __init__(self, folder, prefix, params, q_fit, I_fit, q=None, I=None, error=None, I_density=None):
        self.folder = folder
        self.prefix = prefix
        self.params = params
        self.q_fit, self.I_fit = q_fit, I_fit
        self.q, self.I, self.error, self.I_density = q, I, error, I_density

    @property
    def Rg(self):
        return self.params.get("Rg", np.nan)

    @property
    def Iz(self):
        return self.params.get("I0", np.nan)

    def __repr__(self):
        p = self.params
        return (f"DenssFit({self.prefix}: Rg={p.get('Rg', np.nan):.1f}, I0={p.get('I0', np.nan):.4g}, "
                f"Dmax={p.get('Dmax', np.nan):.1f}, {0 if self.q is None else len(self.q)} data points)")


_VALUE = re.compile(r"^#\s*([^=\s][^=]*?)\s*=\s*(\S+)(?:\s*\+-\s*(\S+))?\s*$")


def _parse_header(path):
    params = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.startswith("#"):
                break
            m = _VALUE.match(line.rstrip())
            if m is None:
                continue
            key = "I0" if m.group(1) == "I(0)" else m.group(1)
            try:
                params[key] = float(m.group(2))
                if m.group(3) is not None:
                    params[key + "_err"] = float(m.group(3))
            except ValueError:
                continue
    return params


def load_denss_fit(folder, prefix=None):
    """Read one component's DENSS result files.

    Parameters
    ----------
    folder : str
        Folder containing ``<prefix>_fitdata.fit`` (and normally ``<prefix>_map.fit``),
        e.g. ``<analysis>/DENSS/component_1``.
    prefix : str, optional
        File prefix; default: the folder's own name (``component_1``).

    Returns
    -------
    DenssFit

    Raises
    ------
    FileNotFoundError
        If ``<prefix>_fitdata.fit`` is missing (``*_map.fit`` is optional).
    """
    folder = os.path.abspath(folder)
    if prefix is None:
        prefix = os.path.basename(folder)
    fit_path = os.path.join(folder, f"{prefix}_fitdata.fit")
    if not os.path.exists(fit_path):
        raise FileNotFoundError(f"{fit_path} not found (expected the DENSS result of '{prefix}' in {folder})")
    params = _parse_header(fit_path)
    fit_table = np.loadtxt(fit_path, comments="#", ndmin=2)

    q = I = error = I_density = None
    map_path = os.path.join(folder, f"{prefix}_map.fit")
    if os.path.exists(map_path):
        with open(map_path, encoding="utf-8", errors="replace") as fh:
            m = re.search(r"chi2\s*=\s*([-+0-9.eE]+)", fh.readline())
        if m:
            params["chi2"] = float(m.group(1))
        q, I, error, I_density = np.loadtxt(map_path, comments="#", ndmin=2).T
    return DenssFit(folder, prefix, params, fit_table[:, 0], fit_table[:, 3], q, I, error, I_density)


def load_denss_components(denss_folder):
    """Read all ``component_N`` subfolders of a DENSS result folder, ordered by N.

    Returns
    -------
    list of DenssFit
    """
    names = [d for d in os.listdir(denss_folder)
             if re.fullmatch(r"component_\d+", d) and os.path.isdir(os.path.join(denss_folder, d))]
    names.sort(key=lambda d: int(d.split("_")[1]))
    if not names:
        raise FileNotFoundError(f"no component_N folders in {denss_folder}")
    return [load_denss_fit(os.path.join(denss_folder, d)) for d in names]


def denss_profiles_on_common_q(fits, q=None):
    """Stack the data profiles of several :class:`DenssFit` on one q grid.

    Parameters
    ----------
    fits : list of DenssFit
    q : ndarray, optional
        Target grid; default the first fit's data ``q``. Values outside a fit's own q range are
        clamped to its end values, so pick a grid inside all ranges.

    Returns
    -------
    q, P : ndarray (n_q,), ndarray (n_q, n_components)
        Directly usable as ``compute_shape_match_scores(q, P, fits)``.
    """
    if any(f.q is None for f in fits):
        raise ValueError("a DenssFit has no data (its *_map.fit is missing)")
    if q is None:
        q = fits[0].q
    P = np.array([np.interp(q, f.q, f.I) for f in fits]).T
    return np.asarray(q), P
