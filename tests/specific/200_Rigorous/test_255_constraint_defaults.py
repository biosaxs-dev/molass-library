"""Tests for ConstraintDefaults.get_constraint_and_overrides (issue #255).

Single source of truth for the auto-applied DE/LumpingConstraint condition
and its accompanying solver-setting overrides, shared by RigorousImplement.py
(parent process) and RecipeRunner.py (subprocess) so a future safety override
can't be added to one copy and forgotten in the other (as happened with
de_tol in #253).
"""
import io
import contextlib
import warnings


def _make_decomp(num_components):
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD

    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()), \
         warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ssd = SSD(SAMPLE1)
        trimmed = ssd.trimmed_copy()
        corrected = trimmed.corrected_copy()
        decomp = corrected.quick_decomposition(num_components=num_components)
    return decomp


def test_no_auto_apply_below_three_components():
    from molass.Rigorous.ConstraintDefaults import get_constraint_and_overrides
    decomp = _make_decomp(2)
    constraints, overrides = get_constraint_and_overrides('DE', 2, decomp)
    assert constraints is None
    assert overrides == {}


def test_no_auto_apply_for_non_de_method():
    from molass.Rigorous.ConstraintDefaults import get_constraint_and_overrides
    decomp = _make_decomp(3)
    constraints, overrides = get_constraint_and_overrides('BH', 3, decomp)
    assert constraints is None
    assert overrides == {}


def test_auto_apply_for_de_three_plus_components():
    from molass.Rigorous.ConstraintDefaults import get_constraint_and_overrides
    from molass.Rigorous.LumpingConstraint import LumpingConstraint
    decomp = _make_decomp(3)

    constraints, overrides = get_constraint_and_overrides('DE', 3, decomp)

    assert isinstance(constraints, list) and len(constraints) == 1
    assert isinstance(constraints[0], LumpingConstraint)
    assert overrides == {'de_tol': 0}


def test_method_case_insensitive():
    from molass.Rigorous.ConstraintDefaults import get_constraint_and_overrides
    decomp = _make_decomp(3)
    constraints, overrides = get_constraint_and_overrides('de', 3, decomp)
    assert constraints is not None
    assert overrides == {'de_tol': 0}
