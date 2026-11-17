"""quiet_legacy: the printed output of legacy code is discarded unless debug=True (molass-library#398)."""
import sys
import warnings
from types import SimpleNamespace

import numpy as np
import pytest

from molass.Global.Quiet import quiet_legacy


def _noisy():
    print("get_peak_boundaries: peak_top_x= [1 2 3]")
    print("AssertionWarning traceback ...", file=sys.stderr)


def test_output_is_discarded_and_debug_shows_it(capsys):
    with quiet_legacy():
        _noisy()
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
    with quiet_legacy(debug=True):
        _noisy()
    captured = capsys.readouterr()
    assert "get_peak_boundaries" in captured.out and "AssertionWarning" in captured.err


def test_numerical_warnings_are_discarded_but_user_warnings_of_molass_are_kept():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with quiet_legacy():
            warnings.warn("invalid value encountered in divide", RuntimeWarning)
            warnings.warn("num_components=4 does not match", UserWarning)
    assert [str(w.message) for w in caught] == ["num_components=4 does not match"]


def test_the_output_of_a_failing_call_is_attached_to_the_exception():
    with pytest.raises(ValueError) as info:
        with quiet_legacy():
            print("the line that explains it")
            raise ValueError("boom")
    notes = "\n".join(getattr(info.value, "__notes__", []))
    assert "the line that explains it" in notes and "debug=True" in notes


def test_a_failure_without_output_gets_no_note():
    with pytest.raises(ValueError) as info:
        with quiet_legacy():
            raise ValueError("boom")
    assert not getattr(info.value, "__notes__", [])


def test_the_values_of_the_block_are_returned_normally():
    def compute():
        with quiet_legacy():
            _noisy()
            return 42
    assert compute() == 42


def _fake_decomposition(monkeypatch):
    import molass.Rigorous.LegacyBridgeUtils as bridge

    def make_basecurves(decomp, debug=False):
        _noisy()
        return None, ["baseparams"]
    monkeypatch.setattr(bridge, "make_basecurves_from_decomposition", make_basecurves)
    return SimpleNamespace(
        make_rigorous_initparams=lambda baseparams, debug=False: (_noisy(), np.arange(7.0))[1])


def test_get_rigorous_initparams_is_quiet_unless_debug(monkeypatch, capsys):
    from molass.LowRank.Decomposition import Decomposition
    fake = _fake_decomposition(monkeypatch)
    fake.get_rigorous_initparams = lambda debug=False: Decomposition.get_rigorous_initparams(fake, debug=debug)
    assert len(Decomposition.get_rigorous_initparams(fake)) == 7
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
    Decomposition.get_rigorous_initparams(fake, debug=True)
    assert "get_peak_boundaries" in capsys.readouterr().out
    assert Decomposition.get_rigorous_param_count(fake) == 7
    assert capsys.readouterr().out == ""


def test_upgrade_is_quiet_unless_debug(monkeypatch, capsys):
    from molass.LowRank.Decomposition import Decomposition
    import molass.SEC.ModelFactory as factory

    class Model:
        def optimize_decomposition(self, decomposition, **kwargs):
            _noisy()
            return "upgraded"
    monkeypatch.setattr(factory, "create_model", lambda model, debug=False: Model())
    import molass.LowRank.Decomposition as decomposition_module
    monkeypatch.setattr(decomposition_module, "reload", lambda module: module)     # debug=True reloads the factory
    assert Decomposition.upgrade(SimpleNamespace(), "GRM") == "upgraded"
    assert capsys.readouterr().out == ""
    Decomposition.upgrade(SimpleNamespace(), "GRM", debug=True)
    assert "get_peak_boundaries" in capsys.readouterr().out
