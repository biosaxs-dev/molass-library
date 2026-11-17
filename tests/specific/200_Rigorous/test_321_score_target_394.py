"""Decomposition.score() of a result loaded from a rigorous job (molass-library#394): which decomposition the optimizer
is built from and which parameters are evaluated. Fast: no optimizer is built."""
from types import SimpleNamespace

import numpy as np
import pytest

from molass.LowRank.Decomposition import Decomposition


def _call_score(monkeypatch, fake):
    calls = []
    import molass.Rigorous.Score as score_module
    monkeypatch.setattr(score_module, "make_score_impl",
                        lambda target, **kwargs: calls.append((target, kwargs)) or "score")
    assert Decomposition.score(fake, trimmed_ssd="trimmed") == "score"
    return calls[0]


def test_a_loaded_result_is_scored_on_the_optimizer_of_the_decomposition_the_run_started_from(monkeypatch):
    basis = SimpleNamespace(has_rg_curve=True)
    params = np.arange(5.0)
    loaded = SimpleNamespace(has_rg_curve=False, _rigorous_params=params, _rigorous_basis=basis)
    target, kwargs = _call_score(monkeypatch, loaded)
    assert target is basis and kwargs["params"] is params


def test_the_rg_curve_check_is_made_on_the_basis(monkeypatch, recwarn):
    basis = SimpleNamespace(has_rg_curve=True)
    loaded = SimpleNamespace(has_rg_curve=False, _rigorous_params=np.zeros(3), _rigorous_basis=basis)
    _call_score(monkeypatch, loaded)
    assert not [w for w in recwarn if "Rg curve not pre-computed" in str(w.message)]


def test_a_decomposition_that_is_not_a_loaded_result_is_scored_from_its_own_curves(monkeypatch):
    plain = SimpleNamespace(has_rg_curve=True, _rigorous_params=None, _rigorous_basis=None)
    target, kwargs = _call_score(monkeypatch, plain)
    assert target is plain and kwargs["params"] is None


def test_copies_of_a_loaded_result_do_not_carry_its_parameters():
    # upgrade() and copy_with_new_components() build a new Decomposition: another model or other curves
    import inspect
    source = inspect.getsource(Decomposition.copy_with_new_components)
    assert "_rigorous_params" not in source and "_rigorous_basis" not in source
