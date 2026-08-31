"""
    molass.Solvers.DE.SolverDE

    Differential Evolution solver using scipy.optimize.differential_evolution.

    Drop-in replacement for SolverBH / SolverCMA in the rigorous optimization
    pipeline. Interface matches SolverCMA.minimize() so it can be wired into
    BasicOptimizer.solve() with method='de'.

    Parameters are in the normalized [0, 10] space used throughout the
    molass-legacy optimizer infrastructure.

    Notes
    -----
    DE is a population-based method: every generation evaluates `pop_size`
    candidate solutions in sequence.  The evaluation budget is:
        max_fevals = niter * FEVALS_PER_NITER
        max_gen    = max_fevals // pop_size   (≥ 1)

    With the default pop_size=None the population is sized automatically by
    scipy (typically 15).

    Unlike CMA-ES (pycma), scipy's DE is NumPy-based and does NOT trigger
    the ProactorEventLoop / BLAS C-extension race that caused the molass-library
    #193 async crash.  It is therefore safe to run with in_process=True and
    async_=True.

    Copyright (c) 2026, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.optimize import differential_evolution, OptimizeResult

# Map from OptStrategyDialog GUI label format → scipy accepted format.
# The GUI dialog stores labels like "DE/best/1/bin" in SerialSettings, but
# scipy.optimize.differential_evolution expects "best1bin".
# Any string not in this map is passed through unchanged (already scipy format).
_STRATEGY_MAP = {
    "DE/best/1/bin":          "best1bin",
    "DE/best/1/exp":          "best1exp",
    "DE/rand/1/bin":          "rand1bin",
    "DE/rand/1/exp":          "rand1exp",
    "DE/best/2/bin":          "best2bin",
    "DE/rand/2/bin":          "rand2bin",
    "DE/rand/2/exp":          "rand2exp",
    "DE/currenttobest/1/bin": "currenttobest1bin",
}

# Evaluation budget multiplier: max_fevals = niter * FEVALS_PER_NITER.
# BH's niter counts hops; each hop runs a full Nelder-Mead local optimization
# which costs ~6,600 evaluations for a 33-parameter GRM problem (measured in
# experiment 30, molass-researcher).  FEVALS_PER_NITER = 6600 makes niter=100
# for DE comparable to niter=100 for BH (~660,000 evaluations each).
# (SolverCMA used 200, copied from CMA, not calibrated against BH.)
# See: https://github.com/biosaxs-dev/molass-library/issues/229
FEVALS_PER_NITER = 6600


class SolverDE:
    """Differential Evolution solver using scipy.

    Parameters
    ----------
    optimizer : BasicOptimizer
        Fully constructed optimizer that provides ``minima_callback``.
    pop_size : int or None
        Population size multiplier (scipy uses popsize * n_var).
        None → scipy default (15).
    strategy : str
        DE strategy, e.g. ``"best1bin"``, ``"rand1bin"``.
        See scipy.optimize.differential_evolution for full list.
    recombination : float
        Crossover probability (0–1).
    mutation : float or tuple
        Differential weight (mutation factor).  A tuple ``(min, max)``
        enables dithering.
    """

    def __init__(self, optimizer, pop_size=None, strategy="best1bin",
                 recombination=0.7, mutation=0.5, tol=None):
        self.optimizer = optimizer
        self._pop_size = pop_size if pop_size is not None else 15
        self.strategy = _STRATEGY_MAP.get(strategy, strategy)  # normalize GUI label → scipy format
        self.recombination = recombination
        self.mutation = mutation
        self._tol = tol if tol is not None else 0.01   # convergence tolerance (default matches scipy)

    def minimize(self, objective, init_params, niter=100, seed=1234,
                 bounds=None, narrow_bounds=False, show_history=False):
        """Run DE minimization.

        Parameters
        ----------
        objective : callable
            Objective function f(x) → scalar (wrapped by
            ``BasicOptimizer.objective_func_wrapper``).
        init_params : ndarray
            Initial parameter vector in normalized [0, 10] space.
        niter : int
            Controls evaluation budget: max_fevals = niter * FEVALS_PER_NITER.
        seed : int
            RNG seed.
        bounds : ndarray of shape (n, 2), optional
            Per-parameter [lower, upper] bounds in normalized space.
            Defaults to [0, 10] for every parameter.
        narrow_bounds : bool
            If True, restrict search to [init_params ± 1.0].
        show_history : bool
            Unused (kept for API parity with SolverBH).

        Returns
        -------
        scipy.optimize.OptimizeResult
            ``.x``   — best parameter vector found
            ``.fun`` — objective value at best x
            ``.nit`` — number of DE generations completed
            ``.nfev``— total function evaluations
        """
        n = len(init_params)

        # ── bounds ──────────────────────────────────────────────────────────
        if narrow_bounds and bounds is None:
            lower = init_params - 1.0
            upper = init_params + 1.0
            bounds_list = [(lower[i], upper[i]) for i in range(n)]
        elif bounds is not None:
            bounds_list = [(bounds[i, 0], bounds[i, 1]) for i in range(n)]
        else:
            bounds_list = [(0.0, 10.0)] * n

        # ── budget ───────────────────────────────────────────────────────────
        max_fevals = niter * FEVALS_PER_NITER
        # scipy uses maxiter = number of generations, not total fevals
        # with popsize multiplier, actual pop = popsize * n_var
        # so maxiter ≈ max_fevals / (popsize * n_var)
        actual_popsize = self._pop_size * n
        maxiter = max(1, max_fevals // actual_popsize)

        # ── callback wrapper ─────────────────────────────────────────────────
        minima_callback = self.optimizer.minima_callback
        stop_event = getattr(self.optimizer, '_stop_event', None)

        def callback_wrapper(xk, convergence=None):
            """Called after each generation with current best."""
            fv = float(objective(xk))
            minima_callback(xk, fv, True)
            
            # cooperative stop (Terminate button)
            if stop_event is not None and stop_event.is_set():
                return True  # tells scipy to stop
            return False

        # ── run scipy differential_evolution ─────────────────────────────────
        # Clamp x0 to bounds: scipy DE strictly rejects x0 outside bounds,
        # while SolverBH silently accepts it. The clamped starting point is
        # the nearest feasible point, which is still a valid warm start.
        bounds_lo = np.array([b[0] for b in bounds_list])
        bounds_hi = np.array([b[1] for b in bounds_list])
        init_params_clamped = np.clip(init_params, bounds_lo, bounds_hi)

        # ── population initialization ─────────────────────────────────────────
        # When seed_params was supplied to optimize_rigorously(), RigorousImplement
        # sets optimizer._de_use_tight_init=True to signal that the entire population
        # should be concentrated near init_params_clamped (the seed).
        #
        # This uses scipy's init=array feature (explicitly documented for this use
        # case: "create a tight bunch of initial guesses in a location where the
        # solution is known to exist").
        #
        # tight_scale=0.1 → σ = 0.1 × 10 = 1.0 in normalized [0,10] space.
        # For a 29-parameter SDM problem with K-bounds [68.5, 913.6], σ_K ≈ 84.5
        # physical units — keeps most members within the correct-assignment basin
        # near the BH seed while still allowing DE to refine.
        #
        # Member 0 is additionally forced to exact init_params_clamped via x0=,
        # ensuring the seed itself is always in the initial population.
        use_tight = getattr(self.optimizer, '_de_use_tight_init', False)
        tight_scale = getattr(self.optimizer, '_de_tight_scale', 0.1)

        if use_tight:
            rng_tight = np.random.default_rng(seed)
            tight_pop = (init_params_clamped
                         + tight_scale * 10.0
                         * rng_tight.standard_normal((actual_popsize, n)))
            tight_pop = np.clip(tight_pop, bounds_lo, bounds_hi)
            init_arg = tight_pop   # shape (pop_size, n) — scipy honours this directly
        else:
            init_arg = 'latinhypercube'

        result = differential_evolution(
            objective,
            bounds_list,
            strategy=self.strategy,
            maxiter=maxiter,
            popsize=self._pop_size,
            recombination=self.recombination,
            mutation=self.mutation,
            seed=seed,
            callback=callback_wrapper,
            polish=False,  # no local refinement (keep pure DE behavior)
            init=init_arg,
            x0=init_params_clamped,  # always set member 0 = seed (even for tight init)
            atol=0,
            tol=self._tol,
            updating='immediate',
            workers=1,  # single-threaded for compatibility with callback
        )

        return result
