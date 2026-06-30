"""
Tests for CEDM (Constrained-EDM) parameter class, model tagging,
and G2020 objective function routing.

Covers:
  - EdmComponentCurve model tag 'cedm'
  - CedmParams.split_params_simple round-trip
  - CedmParams.make_bounds_mask dimension
  - FunctionCodeUtils.detect_function_code returns 'G2020'
  - OptimizerUtils.get_function_code('CEDM') returns 'G2020'
"""
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_full_edm_params(t0=100.0, u=1.0, a=1.0, b=0.0, e=0.5, Dz=0.01, cinj=1.0):
    return np.array([t0, u, a, b, e, Dz, cinj], dtype=float)


class _FakeCedmCurve:
    """Minimal stand-in for EdmComponentCurve with model='cedm'."""
    def __init__(self, params):
        self.params = np.asarray(params, dtype=float)
        self.model = 'cedm'

    def get_params(self):
        return self.params


# ---------------------------------------------------------------------------
# EdmComponentCurve model tagging
# ---------------------------------------------------------------------------

def test_edm_component_curve_default_model_is_edm():
    from molass.SEC.Models.EdmComponentCurve import EdmComponentCurve
    x = np.linspace(50, 200, 10)
    p = _make_full_edm_params()
    c = EdmComponentCurve(x, p)
    assert c.model == 'edm'


def test_edm_component_curve_cedm_model():
    from molass.SEC.Models.EdmComponentCurve import EdmComponentCurve
    x = np.linspace(50, 200, 10)
    p = _make_full_edm_params()
    c = EdmComponentCurve(x, p, model='cedm')
    assert c.model == 'cedm'


# ---------------------------------------------------------------------------
# FunctionCodeUtils routing
# ---------------------------------------------------------------------------

def test_detect_function_code_returns_g2020_for_cedm():
    from molass.Rigorous.FunctionCodeUtils import detect_function_code

    class _FakeDecomp:
        def __init__(self):
            self.xr_ccurves = [_FakeCedmCurve(_make_full_edm_params())]

    assert detect_function_code(_FakeDecomp()) == 'G2020'


def test_detect_function_code_returns_none_for_edm():
    from molass.Rigorous.FunctionCodeUtils import detect_function_code

    class _FakeEdmCurve:
        model = 'edm'

    class _FakeDecomp:
        xr_ccurves = [_FakeEdmCurve()]

    # EDM is not in FUNCTION_CODE_MAP and is not 'cedm' → returns None
    assert detect_function_code(_FakeDecomp()) is None


# ---------------------------------------------------------------------------
# OptimizerUtils bidirectional lookup
# ---------------------------------------------------------------------------

def test_model_name_dict_cedm():
    from molass_legacy.Optimizer.OptimizerUtils import MODEL_NAME_DICT, get_function_code
    assert MODEL_NAME_DICT.get('G2020') == 'CEDM'
    assert get_function_code('CEDM') == 'G2020'


# ---------------------------------------------------------------------------
# CedmParams construction and split round-trip
# ---------------------------------------------------------------------------

def _make_cedm_vector(nc):
    """Build a valid CedmParams parameter vector for nc components (nc+1 peaks)."""
    from molass_legacy.ModelParams.CedmParams import CedmParams, NUM_ELEMENT_PARAMS, NUM_COL_PARAMS
    from molass_legacy.ModelParams.BaselineParams import get_num_baseparams
    nb = get_num_baseparams()
    cp = CedmParams(nc + 1)   # n_components includes baseline; CedmParams(n_components) where nc = n_components-1

    n_real = nc  # actual number of SEC-peaks
    xr_abc = np.tile([0.5, 0.1, 1.0], n_real)              # (a, b, cinj) × nc
    xr_base = np.zeros(nb)
    rgs = np.ones(n_real) * 20.0
    mapping = np.array([1.0, 0.0])
    uv_h = np.ones(n_real)
    uv_base = np.zeros(5 + nb)
    mr = np.array([100.0, 200.0])
    col = np.array([80.0, 1.0, 0.45, 0.01])                # t0, u, e, Dz

    full = np.concatenate([xr_abc, xr_base, rgs, mapping, uv_h, uv_base, mr, col])
    assert len(full) == cp.num_params + NUM_COL_PARAMS, (
        f"vector length {len(full)} != {cp.num_params + NUM_COL_PARAMS}"
    )
    return full, cp


@pytest.mark.parametrize("nc", [1, 2, 3])
def test_cedm_params_split_round_trip(nc):
    full, cp = _make_cedm_vector(nc)
    parts = cp.split_params_simple(full)
    xr_abc, xr_base, rgs, (a_mp, b_mp), uv_h, uv_base, (c, d), col = parts

    assert xr_abc.shape == (nc, 3), f"xr_abc shape {xr_abc.shape} != ({nc}, 3)"
    assert len(rgs) == nc
    assert len(col) == 4
    assert a_mp == pytest.approx(1.0)
    assert col[0] == pytest.approx(80.0)   # t0_sh

    # Reconstruct and compare
    reconstructed = np.concatenate([
        xr_abc.flatten(), xr_base, rgs, [a_mp, b_mp],
        uv_h, uv_base, [c, d], col
    ])
    np.testing.assert_array_almost_equal(reconstructed, full)


@pytest.mark.parametrize("nc", [1, 2])
def test_cedm_params_bounds_mask_length(nc):
    full, cp = _make_cedm_vector(nc)
    from molass_legacy.ModelParams.CedmParams import NUM_COL_PARAMS
    mask = cp.make_bounds_mask()
    assert len(mask) == cp.num_params + NUM_COL_PARAMS

    # xr_abc region must be all True
    n_xr = nc * 3
    assert np.all(mask[:n_xr]), "xr_abc params must be masked"

    # cedm col params at the end must be all True
    assert np.all(mask[-NUM_COL_PARAMS:]), "col params must be masked"


@pytest.mark.parametrize("nc", [1, 2])
def test_cedm_params_get_param_bounds_length(nc):
    full, cp = _make_cedm_vector(nc)
    cp.set_x(np.linspace(50, 200, 50))
    bounds = cp.get_param_bounds(full)
    from molass_legacy.ModelParams.CedmParams import NUM_COL_PARAMS
    assert len(bounds) == cp.num_params + NUM_COL_PARAMS, (
        f"bounds length {len(bounds)} != {cp.num_params + NUM_COL_PARAMS}"
    )
    # All bounds should be (lo, hi) tuples with lo <= hi
    for lo, hi in bounds:
        assert lo <= hi, f"invalid bound ({lo}, {hi})"


# ---------------------------------------------------------------------------
# G2020 import
# ---------------------------------------------------------------------------

def test_g2020_class_importable():
    """G2020 should be importable from its expected location."""
    from molass_legacy.ObjectiveFunctions.G2020 import G2020
    assert G2020 is not None


def test_func_importer_returns_g2020():
    """FuncImporter must return the G2020 class by code 'G2020'."""
    from molass_legacy.Optimizer.FuncImporter import import_objective_function
    cls = import_objective_function('G2020')
    assert cls is not None, "import_objective_function('G2020') returned None"
    from molass_legacy.ObjectiveFunctions.G2020 import G2020
    assert cls is G2020
