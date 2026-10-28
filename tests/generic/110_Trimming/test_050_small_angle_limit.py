"""
Small-angle limit of the trimming (molass-library#342).

The default trimming used to cut the lowest-q points at the Guinier start ('guinier'), which hides the
interparticle (rank-2) correction of concentrated samples such as SAMPLE3 (24 points cut). The default is now
the legacy GUI's extended limit ('extended'); 'guinier' and 'none' stay selectable, and the range can be given
explicitly (xr_qr), which is JSON-serializable for recipes.
"""
import warnings
import pytest
from molass_data import SAMPLE3


@pytest.fixture(scope="module")
def ssd():
    from molass.DataObjects import SecSaxsData as SSD
    return SSD(SAMPLE3)


def start_of(trimming):
    return int(trimming.xr_slices[0].start)


def test_010_policies_order_the_start(ssd):
    guinier = ssd.make_trimming(small_angle_limit='guinier')
    extended = ssd.make_trimming(small_angle_limit='extended')
    none = ssd.make_trimming(small_angle_limit='none')
    assert start_of(guinier) == 24                    # the former default
    assert 0 < start_of(extended) < start_of(guinier) # keeps more low-q points
    assert start_of(none) == 0
    assert (guinier.small_angle_limit, extended.small_angle_limit, none.small_angle_limit) == ('guinier', 'extended', 'none')
    # the upper end does not depend on the policy
    assert guinier.xr_slices[0].stop == extended.xr_slices[0].stop == none.xr_slices[0].stop


def test_020_default_is_extended_and_option_switches_it(ssd):
    from molass.Global.Options import get_molass_options, set_molass_options
    assert get_molass_options('small_angle_limit') == 'extended'
    assert ssd.make_trimming().small_angle_limit == 'extended'
    try:
        set_molass_options(small_angle_limit='guinier')
        assert start_of(ssd.make_trimming()) == 24
        with pytest.raises(ValueError):
            set_molass_options(small_angle_limit='everything')
    finally:
        set_molass_options(small_angle_limit='extended')


def test_030_trimmed_copy_xr_qr_and_json_roundtrip(ssd):
    import json
    xr_qr = json.loads(json.dumps([0, 700]))          # a list, as read back from a recipe
    trimmed = ssd.trimmed_copy(xr_qr=xr_qr)
    assert trimmed.trimming.small_angle_limit == 'explicit'
    assert trimmed.xr.M.shape[0] == 700
    assert trimmed.xr.qv[0] == pytest.approx(ssd.xr.qv[0])
    with pytest.raises(AssertionError):
        ssd.trimmed_copy(trimming=ssd.make_trimming(), xr_qr=(0, 700))


def test_040_recipe_records_the_range_and_old_recipes_keep_the_old_default(ssd):
    from molass.Rigorous.RecipeRunner import _trim_kwargs_from_recipe
    # an old recipe (no xr_qr) is rebuilt with the former default
    assert _trim_kwargs_from_recipe({'trim_params': {}}) == {'small_angle_limit': 'guinier'}
    # a new recipe pins the recorded range
    assert _trim_kwargs_from_recipe({'trim_params': {}, 'xr_qr': [4, 770]}) == {'xr_qr': (4, 770)}
    # explicit trim_params win
    assert _trim_kwargs_from_recipe({'trim_params': {'xr_qr': [0, 700]}, 'xr_qr': [4, 770]}) == {'xr_qr': [0, 700]}
    assert _trim_kwargs_from_recipe({'trim_params': {'small_angle_limit': 'none'}}) == {'small_angle_limit': 'none'}

    from molass.Rigorous.RigorousImplement import build_pipeline_recipe

    class Stub:        # only what build_pipeline_recipe reads from the decomposition
        num_components = 1
        xr_ccurves = [type('C', (), {'model': 'egh'})()]
        ssd = None
    trimmed = ssd.trimmed_copy()
    recipe = build_pipeline_recipe(Stub(), ssd=trimmed)
    assert recipe['xr_qr'] == [start_of(trimmed.trimming), int(trimmed.trimming.xr_slices[0].stop)]


def test_050_rank2_warns_when_low_q_was_cut_at_the_guinier_start(ssd):
    trimmed = ssd.trimmed_copy(small_angle_limit='guinier').corrected_copy()
    decomp = trimmed.quick_decomposition(num_components=1)
    with pytest.warns(UserWarning, match="lowest-q points"):
        decomp.update_xr_ranks([2])
    # rank 1, or the default range, or an explicit range: no warning
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        decomp.update_xr_ranks([1])
        default = ssd.trimmed_copy().corrected_copy().quick_decomposition(num_components=1)
        default.update_xr_ranks([2])
        explicit = ssd.trimmed_copy(xr_qr=(0, 770)).corrected_copy().quick_decomposition(num_components=1)
        explicit.update_xr_ranks([2])
