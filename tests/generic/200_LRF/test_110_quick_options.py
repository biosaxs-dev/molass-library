"""molass-library#301: the options of quick_decomposition are defined once (LowRank/QuickOptions.py)."""
import inspect
import warnings

import pytest

from molass.DataObjects import SecSaxsData as SSD
from molass.LowRank.QuickOptions import (
    DOC_MARKER, INTERNAL_OPTIONS, KNOWN_KWARGS, QUICK_OPTIONS, check_known_kwargs,
)


def test_every_documented_option_is_known_and_in_the_docstring():
    doc = inspect.cleandoc(SSD.quick_decomposition.__doc__)
    assert DOC_MARKER not in doc
    for opt in QUICK_OPTIONS:
        assert opt.name in KNOWN_KWARGS
        assert f"\n{opt.name} : {opt.type}\n" in doc, f"{opt.name} missing from the rendered docstring"


def test_option_names_are_unique_and_disjoint_from_internal():
    names = [o.name for o in QUICK_OPTIONS]
    assert len(names) == len(set(names))
    assert not set(names) & set(INTERNAL_OPTIONS)


def test_rg_order_weight_default_in_doc_is_the_code_default():
    from molass.Decompose.RgOrder import DEFAULT_RG_ORDER_WEIGHT
    rg_doc = next(o.doc for o in QUICK_OPTIONS if o.name == "rg_order_weight")
    assert f"Default {DEFAULT_RG_ORDER_WEIGHT:g};" in rg_doc


def test_known_kwargs_do_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        check_known_kwargs({name: None for name in KNOWN_KWARGS})


def test_typo_warns_at_the_callers_line():
    """The warning must point at the code calling quick_decomposition(), not at library internals."""
    with pytest.warns(UserWarning, match="unrecognized keyword arguments") as rec:
        try:
            SSD.quick_decomposition(object(), num_components=2, rg_order_weigth=0.1)
        except Exception:
            pass    # only the validation at the top is under test
    assert rec[0].filename == __file__
    assert "rg_order_weigth" in str(rec[0].message)
