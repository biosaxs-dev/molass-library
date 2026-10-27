"""molass-library#338: AttributeError on data objects lists close names and aliases."""
import copy
import pickle

import numpy as np
import pytest

from molass.DataObjects.XrData import XrData
from molass.DataObjects.UvData import UvData
from molass.Guinier.RgCurve import RgCurve
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
