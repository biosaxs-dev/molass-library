"""
Test that DE gets a tight (Gaussian-cloud) population init when resuming from
a previous round's best (clear_jobs=False), instead of always using scipy's
plain latinhypercube regardless of the reseed.

Without this, DE's reseeded init_params only ever replaced 1 of
popsize*n_params population members (scipy's x0= argument) -- evolutionarily
negligible, which is why DE's `num_jobs` rounds plateaued instead of
improving like BH's did (see molass-researcher experiments/36_bh_cutomize_trial).

See: https://github.com/biosaxs-dev/molass-library/issues/259

Only the in-process half is covered here (fast: niter=1, in_process=True,
async_=False). The subprocess mirror (RecipeRunner.create_optimizer_from_recipe)
is not covered by a fast unit test -- exercising it needs the full
SSD+decomp+recipe.json+subprocess pipeline (heavy, ~30-100s+), the same
cost/benefit tradeoff already accepted for the analogous de_tol subprocess
mirror fix (no fast test either; see repo memory
de-tol-subprocess-premature-convergence.md).
"""
import io
import contextlib
import warnings


def _make_decomp():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD

    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()), \
         warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ssd = SSD(SAMPLE1)
        trimmed = ssd.trimmed_copy()
        corrected = trimmed.corrected_copy()
        decomp = corrected.quick_decomposition(num_components=2)
    return trimmed, corrected, decomp


def test_de_tight_init_not_set_on_fresh_run(tmp_path):
    """A fresh DE round (clear_jobs=True) must NOT set _de_use_tight_init."""
    trimmed, corrected, decomp = _make_decomp()
    analysis_folder = str(tmp_path / "test_run")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        run_info = decomp.optimize_rigorously(
            analysis_folder=analysis_folder,
            method='DE', niter=1,
            in_process=True, async_=False, monitor=False,
            clear_jobs=True,
        )

    assert not getattr(run_info.optimizer, '_de_use_tight_init', False)


def test_de_tight_init_set_on_resumed_run(tmp_path):
    """A resumed DE round (clear_jobs=False, a previous job exists) must set it."""
    trimmed, corrected, decomp = _make_decomp()
    analysis_folder = str(tmp_path / "test_run")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # Round 0: fresh, produces a real job 000 with a matching-length init_params.
        run0 = decomp.optimize_rigorously(
            analysis_folder=analysis_folder,
            method='DE', niter=1,
            in_process=True, async_=False, monitor=False,
            clear_jobs=True,
        )
        assert not getattr(run0.optimizer, '_de_use_tight_init', False)

        # Round 1: resumed -- _load_best_init_params() finds round 0's job and
        # reseeds, which must now also set _de_use_tight_init.
        run1 = decomp.optimize_rigorously(
            analysis_folder=analysis_folder,
            method='DE', niter=1,
            in_process=True, async_=False, monitor=False,
            clear_jobs=False,
        )

    assert getattr(run1.optimizer, '_de_use_tight_init', False) is True


def test_bh_never_sets_de_tight_init(tmp_path):
    """BH resuming (clear_jobs=False) must not set the DE-only flag (harmless either way,
    but confirms the guard is method-scoped, not accidentally global)."""
    trimmed, corrected, decomp = _make_decomp()
    analysis_folder = str(tmp_path / "test_run")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        run0 = decomp.optimize_rigorously(
            analysis_folder=analysis_folder,
            method='BH', niter=1,
            in_process=True, async_=False, monitor=False,
            clear_jobs=True,
        )
        run1 = decomp.optimize_rigorously(
            analysis_folder=analysis_folder,
            method='BH', niter=1,
            in_process=True, async_=False, monitor=False,
            clear_jobs=False,
        )

    assert not getattr(run0.optimizer, '_de_use_tight_init', False)
    assert not getattr(run1.optimizer, '_de_use_tight_init', False)
