"""
Tests for EDM (constrained/shared-column) parameter class, model tagging,
and G2020 objective function routing.

Covers:
  - EdmComponentCurve model tag 'edm'
  - EdmParams.split_params_simple round-trip
  - EdmParams.make_bounds_mask dimension
  - FunctionCodeUtils.detect_function_code returns 'G2020'
  - OptimizerUtils.get_function_code('EDM') returns 'G2020'
"""
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_full_edm_params(t0=100.0, u=1.0, a=1.0, b=0.0, e=0.5, Dz=0.01, cinj=1.0):
    return np.array([t0, u, a, b, e, Dz, cinj], dtype=float)


class _FakeEdmCurve:
    """Minimal stand-in for EdmComponentCurve with model='edm'."""
    def __init__(self, params):
        self.params = np.asarray(params, dtype=float)
        self.model = 'edm'

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


# ---------------------------------------------------------------------------
# FunctionCodeUtils routing
# ---------------------------------------------------------------------------

def test_detect_function_code_returns_g2020_for_edm():
    from molass.Rigorous.FunctionCodeUtils import detect_function_code

    class _FakeDecomp:
        def __init__(self):
            self.xr_ccurves = [_FakeEdmCurve(_make_full_edm_params())]

    assert detect_function_code(_FakeDecomp()) == 'G2020'


# ---------------------------------------------------------------------------
# OptimizerUtils bidirectional lookup
# ---------------------------------------------------------------------------

def test_model_name_dict_edm():
    from molass_legacy.Optimizer.OptimizerUtils import MODEL_NAME_DICT, get_function_code
    assert MODEL_NAME_DICT.get('G2020') == 'EDM'
    assert get_function_code('EDM') == 'G2020'


# ---------------------------------------------------------------------------
# EdmParams construction and split round-trip
# ---------------------------------------------------------------------------

def _make_edm_vector(nc):
    """Build a valid EdmParams parameter vector for nc components (nc+1 peaks)."""
    from molass_legacy.ModelParams.EdmParams import EdmParams, NUM_ELEMENT_PARAMS, NUM_COL_PARAMS
    from molass_legacy.ModelParams.BaselineParams import get_num_baseparams
    nb = get_num_baseparams()
    cp = EdmParams(nc + 1)   # n_components includes baseline; EdmParams(n_components) where nc = n_components-1

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
def test_edm_params_split_round_trip(nc):
    full, cp = _make_edm_vector(nc)
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
def test_edm_params_bounds_mask_length(nc):
    full, cp = _make_edm_vector(nc)
    from molass_legacy.ModelParams.EdmParams import NUM_COL_PARAMS
    mask = cp.make_bounds_mask()
    assert len(mask) == cp.num_params + NUM_COL_PARAMS

    # xr_abc region must be all True
    n_xr = nc * 3
    assert np.all(mask[:n_xr]), "xr_abc params must be masked"

    # edm col params at the end must be all True
    assert np.all(mask[-NUM_COL_PARAMS:]), "col params must be masked"


@pytest.mark.parametrize("nc", [1, 2])
def test_edm_params_get_param_bounds_length(nc):
    full, cp = _make_edm_vector(nc)
    cp.set_x(np.linspace(50, 200, 50))
    bounds = cp.get_param_bounds(full)
    from molass_legacy.ModelParams.EdmParams import NUM_COL_PARAMS
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


# ---------------------------------------------------------------------------
# ModelFactory 'edm' / removed free-EDM coverage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("model_name", ["edm", "EDM"])
def test_model_factory_defaults_shared_column_true(model_name):
    """'edm' (any case) must default to shared_column=True."""
    from molass.SEC.ModelFactory import create_model
    model = create_model(model_name)
    assert model.kwargs.get('shared_column') is True


@pytest.mark.parametrize("model_name", ["cedm", "CEDM"])
def test_model_factory_rejects_cedm(model_name):
    """'cedm' is no longer a recognized model name; only 'edm' is."""
    from molass.SEC.ModelFactory import create_model
    with pytest.raises(ValueError, match="Unknown model name"):
        create_model(model_name)


def test_model_factory_explicit_shared_column_still_overridable():
    """Explicit shared_column kwarg must still take precedence over the
    default (validated at actual-optimization time, not construction time)."""
    from molass.SEC.ModelFactory import create_model
    model = create_model('edm', shared_column=False)
    assert model.kwargs.get('shared_column') is False


def test_edm_optimizer_shared_column_false_raises():
    """The free-EDM (shared_column=False) path has been removed."""
    from molass.SEC.Models.EdmOptimizer import optimize_edm_xr_decomposition

    class _FakeICurve:
        def get_xy(self):
            return np.linspace(0, 100, 50), np.ones(50)

    class _FakeXrCcurve:
        def __init__(self):
            self.x = np.linspace(0, 100, 50)
            self.y = np.ones(50)

    class _FakeDecomp:
        num_components = 1
        xr_icurve = _FakeICurve()
        xr_ccurves = [_FakeXrCcurve()]

    init_params = _make_full_edm_params().reshape(1, 7)
    with pytest.raises(ValueError, match="shared_column=False"):
        optimize_edm_xr_decomposition(_FakeDecomp(), init_params, shared_column=False)
