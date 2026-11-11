"""molass-library#338: AttributeError on data objects lists close names and aliases."""
import copy
import pickle

import numpy as np
import pytest

from molass.DataObjects.XrData import XrData
from molass.DataObjects.UvData import UvData
from molass.Guinier.RgCurve import RgCurve
from molass.LowRank.Component import XrComponent, UvComponent
from molass.Global.DidYouMean import suggest_names, DidYouMeanMixin


@pytest.fixture
def xr():
    return XrData(np.ones((5, 7)), np.linspace(0.01, 0.2, 5), np.arange(1, 8))


def test_xr_qvector_suggests_qv(xr):
    with pytest.raises(AttributeError, match=r"no attribute 'qvector'\. Did you mean: 'qv'") as e:
        xr.qvector
    assert e.value.name == "qvector"


def test_uv_wavelength_suggests_wv():
    uv = UvData(np.ones((4, 7)), np.linspace(250, 400, 4), np.arange(3, 10))
    with pytest.raises(AttributeError, match="Did you mean: 'wv'"):
        uv.wavelength


def test_spelling_matches_without_a_hint(xr):
    with pytest.raises(AttributeError, match="Did you mean: .*'get_icurve'"):
        xr.get_icurv


def test_rgcurve_indices_suggests_frames():
    rg = RgCurve([1, 2, 3], np.array([30.0, 30.0, 30.0]), np.ones(3))
    with pytest.raises(AttributeError, match="Did you mean: 'frames'"):
        rg.indices


def test_no_suggestion_for_unrelated_name(xr):
    with pytest.raises(AttributeError) as e:
        xr.zzzzzzzz
    assert "Did you mean" not in str(e.value)


def test_hasattr_getattr_default_copy_and_pickle_still_work(xr):
    assert not hasattr(xr, "qvector") and getattr(xr, "qvector", 42) == 42
    assert copy.deepcopy(xr).M.shape == (5, 7)
    assert pickle.loads(pickle.dumps(xr)).jv.tolist() == xr.jv.tolist()


def test_error_inside_a_property_is_not_masked():
    class Thing(DidYouMeanMixin):
        @property
        def broken(self):
            raise AttributeError("inner problem")

    with pytest.raises(AttributeError, match="inner problem"):
        Thing().broken


def test_suggest_names_prefers_the_hint(xr):
    assert suggest_names(xr, "q_vector")[0] == "qv"


# components (molass-library#385)
@pytest.fixture
def component():
    x = np.arange(20.0)
    icurve = np.array([x, np.exp(-0.5*((x - 9)/3.0)**2)])
    q = np.linspace(0.01, 0.2, 10)
    jcurve = np.array([q, np.exp(-q**2*900/3), np.full(10, 0.01)]).T
    return XrComponent(icurve, jcurve, np.ones(20))


@pytest.mark.parametrize("guess, target", [("get_rg", "compute_rg"), ("rg", "compute_rg"),
                                           ("radius_of_gyration", "compute_rg"),
                                           ("get_peak_top_x", "peak_index"), ("peak_position", "peak_index"),
                                           ("get_mass", "get_volume_mass"), ("get_guinier", "get_guinier_object")])
def test_component_guesses_name_the_working_attribute(component, guess, target):
    with pytest.raises(AttributeError, match=rf"no attribute '{guess}'\. Did you mean: .*'{target}'"):
        getattr(component, guess)


def test_uv_component_has_the_hints_too():
    x = np.arange(10.0)
    comp = UvComponent(np.array([x, x]), np.array([x, x, x]).T, np.ones(10))
    with pytest.raises(AttributeError, match="Did you mean: .*'peak_index'"):
        comp.peak_position


def test_component_still_behaves_as_before(component):
    assert not hasattr(component, "get_rg") and getattr(component, "get_rg", 1) == 1
    assert component.peak_index == 9 and component.get_xy()[0][0] == 0
    assert copy.deepcopy(component).peak_index == 9
    assert pickle.loads(pickle.dumps(component)).peak_index == 9
    assert component.sg is None                      # attributes set in __init__ are plain attributes
