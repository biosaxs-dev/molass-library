import json
from types import SimpleNamespace

import numpy as np
import pytest


def test_array_api_matches_guinier_object_api():
    from molass.Kratky.ShapeMatch import compute_shape_match_scores, match_kratky_curves

    q = np.linspace(0.004, 0.2, 220)
    profiles = np.column_stack((np.exp(-(q * 30)**2 / 3), np.exp(-(q * 45)**2 / 3)))
    rgs, i0s = [30.0, 45.0], [1.0, 1.0]
    legacy = compute_shape_match_scores(
        q, profiles, [SimpleNamespace(Rg=rg, Iz=i0) for rg, i0 in zip(rgs, i0s)]
    )
    array_result = match_kratky_curves(q, profiles, rgs, i0s, labels=["first", "second"])

    np.testing.assert_allclose(array_result.score_matrix, legacy.score_matrix)
    assert array_result.component_labels[0].startswith("first ")
    assert array_result.component_labels[1].startswith("second ")


def test_shape_match_result_round_trips_strict_json():
    from molass.Kratky.ShapeMatch import ShapeMatchResult, match_kratky_curves

    q = np.linspace(0.004, 0.2, 220)
    profiles = np.column_stack((np.exp(-(q * 30)**2 / 3), np.exp(-(q * 45)**2 / 3)))
    result = match_kratky_curves(q, profiles, [30.0, np.nan], [1.0, 1.0])
    encoded = json.dumps(result.to_dict(), allow_nan=False)
    restored = ShapeMatchResult.from_dict(json.loads(encoded))

    assert restored.shape_names == result.shape_names
    assert restored.component_labels == result.component_labels
    np.testing.assert_allclose(restored.score_matrix, result.score_matrix, equal_nan=True)
    np.testing.assert_allclose(restored.raw_score_matrix, result.raw_score_matrix, equal_nan=True)
    assert restored.peak_qrgs == result.peak_qrgs
    for before, after in zip(result.kratky_curves, restored.kratky_curves):
        if before is None:
            assert after is None
        else:
            for x0, x1 in zip(before, after):
                np.testing.assert_allclose(x1, x0, equal_nan=True)
    assert restored.best_shape(0)[0] == result.best_shape(0)[0]
    assert np.isnan(restored.best_shape(1)[1])


def test_reference_shapes_can_be_injected_and_reference_curve_is_cached():
    from molass.Kratky.ShapeLibrary import ShapeSpec
    from molass.Kratky.ShapeMatch import match_kratky_curve

    calls = []

    def profile(q):
        calls.append(len(q))
        return np.exp(-q**2)

    shapes = [ShapeSpec("injected", 40.0, profile, lambda ax: 1.0)]
    q = np.linspace(0.004, 0.2, 220)
    intensity = np.exp(-q**2)
    first = match_kratky_curve(q, intensity, 40.0, shapes=shapes)
    calls_after_first = len(calls)
    second = match_kratky_curve(q, intensity, 40.0, shapes=shapes)

    assert first.shape_names == ["injected"]
    assert second.shape_names == ["injected"]
    assert calls_after_first == 1
    assert len(calls) == calls_after_first


def test_array_api_validates_component_dimensions():
    from molass.Kratky.ShapeMatch import compute_shape_match_scores

    q = np.linspace(0.01, 0.2, 10)
    with pytest.raises(ValueError, match="rgs and i0s"):
        compute_shape_match_scores(q, np.ones((10, 2)), rgs=[30.0], i0s=[1.0])
