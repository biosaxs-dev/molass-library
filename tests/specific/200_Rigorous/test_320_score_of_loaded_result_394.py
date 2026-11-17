"""score() of a result loaded from a rigorous job evaluates that job's parameters (molass-library#394)."""
import shutil
import tempfile

import numpy as np
import pytest
from molass_data import SAMPLE1

import molass
from molass.DataObjects import SecSaxsData as SSD
from molass.Rigorous.CurrentStateUtils import load_best_rigorous_result

pytestmark = pytest.mark.slow     # one real DE run


@pytest.fixture(scope="module")
def finished_run():
    trimmed = SSD(SAMPLE1).trimmed_copy()
    decomp = trimmed.corrected_copy().quick_decomposition(num_components=3)
    folder = tempfile.mkdtemp(prefix="test_score_loaded_394_")
    decomp.optimize_rigorously(method='DE', niter=1, async_=False, monitor=False,
                               trimmed_ssd=trimmed, analysis_folder=folder)
    yield decomp, trimmed, folder
    shutil.rmtree(folder, ignore_errors=True)


def test_score_of_a_loaded_result_gives_its_stored_fv(finished_run):
    decomp, trimmed, folder = finished_run
    result = load_best_rigorous_result(decomp, folder)
    assert result._rigorous_params is not None
    score = result.score(trimmed_ssd=trimmed)
    assert score.source == 'rigorous'
    assert score.fv == pytest.approx(result.fv, abs=1e-4)           # callback.txt keeps 6 significant digits
    np.testing.assert_allclose(score.params, result._rigorous_params)


def test_load_analysis_result_scores_like_its_stored_fv(finished_run):
    decomp, trimmed, folder = finished_run
    info = molass.load_analysis(folder)
    assert info.result.score(trimmed_ssd=info.trimmed).fv == pytest.approx(info.result.fv, abs=1e-4)


def test_the_stored_parameters_are_what_is_evaluated(finished_run):
    decomp, trimmed, folder = finished_run
    result = load_best_rigorous_result(decomp, folder)
    perturbed = result._rigorous_params * (1 + 0.01 * np.random.default_rng(0).standard_normal(len(result._rigorous_params)))
    result._rigorous_params = perturbed
    score = result.score(trimmed_ssd=trimmed)
    np.testing.assert_allclose(score.params, perturbed)
    assert abs(score.fv - result.fv) > 1e-3


def test_a_result_without_stored_parameters_is_evaluated_from_its_curves(finished_run):
    decomp, trimmed, folder = finished_run
    result = load_best_rigorous_result(decomp, folder)
    result._rigorous_params = None
    assert result.score(trimmed_ssd=trimmed).source == 'decomp'


def test_stored_parameters_of_the_wrong_length_warn(finished_run):
    decomp, trimmed, folder = finished_run
    result = load_best_rigorous_result(decomp, folder)
    result._rigorous_params = result._rigorous_params[:-1]
    with pytest.warns(UserWarning, match="stored optimized parameters"):
        score = result.score(trimmed_ssd=trimmed)
    assert score.source == 'decomp'
