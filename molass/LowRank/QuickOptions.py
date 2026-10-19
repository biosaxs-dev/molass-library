"""
LowRank.QuickOptions.py

Single definition of the keyword options of ``SecSaxsData.quick_decomposition`` (molass-library#301).

Adding an option means adding one entry to ``QUICK_OPTIONS`` (documented) or ``INTERNAL_OPTIONS``
(accepted but intentionally undocumented) here. The set of accepted keywords, the typo warning and the
"Parameters" entries of the ``quick_decomposition`` docstring are all derived from these tables,
so they cannot drift apart; the plumbing of the value itself stays where it is used.
"""
import inspect
import textwrap
import warnings
from collections import namedtuple

from molass.Decompose.RgOrder import DEFAULT_RG_ORDER_WEIGHT

Option = namedtuple("Option", "name type doc")

DOC_MARKER = "@@QUICK_OPTIONS@@"

QUICK_OPTIONS = [
    Option("proportions", "list of float, optional", """
        Specifies the approximate area ratios of the elution peaks.
        The values do not need to be normalized; for example,
        ``[1, 1]``, ``[0.5, 0.5]``, and ``[3, 3]`` all produce the same result
        because they are normalized internally.

        When this option is given, a **proportional decomposition** algorithm
        is used instead of the default peak-recognition algorithm.
        The proportional algorithm divides the total elution curve by cumulative area
        according to the given ratios, and fits an EGH model to each slice independently.
        This provides better initialization for cases with highly overlapping peaks,
        where the default algorithm may produce unstable results.

        The exact ratios do not need to be known precisely;
        even a rough estimate (e.g., ``[2, 1]`` when the true ratio is ``[1, 1]``)
        is usually sufficient.
    """),
    Option("xslices", "list of slice, optional", """
        Precomputed slices over the XR icurve's frame axis, used instead of deriving
        them from the XR icurve itself. Applies only to the ``proportions`` path.
        Use this for cross-channel slicing when XR baseline noise causes area-based
        slicing to miss small features (e.g. shoulders) that are much clearer in the
        UV icurve -- build boundaries on UV with
        ``molass.Decompose.Proportional.compute_proportional_boundaries()``, remap them
        to XR frames with ``ssd.get_mapping().uv_to_xr()``, then build slices with
        ``molass.Decompose.Proportional.slices_from_boundaries()``. Default None
        (slice the XR icurve itself, original behavior).
    """),
    Option("proportions_source", "{'xr', 'uv'}, optional", """
        Which channel's icurve the ``proportions`` fit is performed on. Default
        ``'xr'`` (fit on XR, derive UV as XR's partner -- original behavior). ``'uv'``
        instead fits fully on the UV icurve -- usually much better signal-to-noise for
        small features such as shoulders next to a dominant peak -- and derives XR as
        UV's partner (mapping shape, refitting only heights). XR remains the shape
        used by the rest of the pipeline (LRF, Rg/Guinier analysis, rigorous
        optimization) either way.
    """),
    Option("rg_order_weight", "float, optional", f"""
        Applies only to the ``proportions`` path with ``proportions_source='xr'``.
        Weight of a soft SEC-order penalty added to the proportional fit: component
        Rgs (a cheap low-q-decay proxy from the LRF of the trial curves) should
        decrease with elution order, as in the rigorous objective. This makes the
        result far less sensitive to tiny input perturbations (trimming slice,
        platform numerics). Default {DEFAULT_RG_ORDER_WEIGHT:g}; ``0`` restores the elution-curve-only fit.
        Ignored for a single component and when ``allow_negative_peaks`` is True.
        See molass-library#295.
    """),
    Option("xr_peakpositions", "list of float, optional", """
        Specifies the frame positions where peaks should be pinned.
        Uses a penalty-based optimizer (Nelder-Mead) that fits EGH peaks
        with a strong position constraint. ``num_components`` is inferred
        from the length if not provided.

        Mutually exclusive with ``proportions``.
    """),
    Option("num_plates", "int, optional", """
        Fallback plate count used to seed the Martin-Synge plate-theory
        estimation (shared injection time and plate count, from which each
        component's Gaussian width is derived -- see
        ``molass.SEC.Models.MartinSynge``) when self-estimation from the
        component-wise (tR, sigma) pairs is degenerate. Applies only to the
        ``proportions`` path. Default 14400.
    """),
    Option("tau_limit", "float, optional", """
        Maximum allowed ratio ``|tau| / sigma`` for positioned decomposition.
        Default 0.6.
    """),
    Option("max_sigma", "float, optional", """
        Maximum allowed Gaussian width (sigma) for positioned decomposition.
        Default 80.
    """),
    Option("min_sigma", "float, optional", """
        Minimum allowed Gaussian width (sigma) for positioned decomposition.
        Default 5.
    """),
    Option("allow_negative_peaks", "bool, optional", """
        If True, allow negative peak heights (H < 0) in the EGH model.
        This enables decomposition of components with negative scattering,
        such as those arising from buffer composition mismatch.
        Default False.
    """),
    Option("debug", "bool, optional", """
        If True, reload internal modules and show diagnostic plots.
        Default False.
    """),
]

# accepted without a public description (legacy/experimental or passed through to lower layers)
INTERNAL_OPTIONS = (
    "randomize", "seed", "global_opt", "area_weight", "sec_constraints", "data_matrix", "qv",
    "curve_model", "smoothing", "decompargs", "peakpositions", "smooth_uv", "consistent_uv",
    "ip_effect_info", "rgcurve",
)

KNOWN_KWARGS = frozenset(o.name for o in QUICK_OPTIONS) | frozenset(INTERNAL_OPTIONS)


def check_known_kwargs(kwargs, stacklevel=3):
    """Warn about keyword arguments that ``quick_decomposition`` does not know (typo guard, issue #64)."""
    unknown = set(kwargs) - KNOWN_KWARGS
    if unknown:
        warnings.warn(
            f"quick_decomposition() received unrecognized keyword arguments: {unknown}. "
            f"Check for typos. Known kwargs: {sorted(KNOWN_KWARGS)}",
            stacklevel=stacklevel,
        )


def render_parameters_doc(indent=0):
    """Numpydoc "Parameters" entries for ``QUICK_OPTIONS``, each line indented by *indent* spaces."""
    pad = " " * indent
    blocks = []
    for opt in QUICK_OPTIONS:
        body = textwrap.indent(inspect.cleandoc(opt.doc), pad + "    ")
        blocks.append(f"{pad}{opt.name} : {opt.type}\n{body}")
    return "\n\n".join(blocks)


def fill_doc(doc):
    """Replace ``DOC_MARKER`` in *doc* by the rendered options, matching the marker's own indentation.

    The indentation is measured, not assumed: since Python 3.13 the compiler strips the common
    indentation of docstrings, older versions keep it.
    """
    lines = doc.split("\n")
    for k, line in enumerate(lines):
        if DOC_MARKER in line:
            indent = len(line) - len(line.lstrip())
            lines[k] = line.replace(DOC_MARKER, render_parameters_doc(indent).lstrip())
            break
    return "\n".join(lines)
