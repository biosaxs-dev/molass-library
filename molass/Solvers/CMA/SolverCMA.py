"""
    molass.Solvers.CMA.SolverCMA

    CMA-ES (Covariance Matrix Adaptation Evolution Strategy) solver.
    Drop-in replacement for SolverBH in the rigorous optimization pipeline.

    Interface matches SolverBH.minimize() so it can be wired into
    BasicOptimizer.solve() with method='cma'.

    Parameters are in the normalized [0, 10] space used throughout the
    molass-legacy optimizer infrastructure.

    Copyright (c) 2026, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.optimize import OptimizeResult

NARROW_BOUNDS_ALLOW = 1.0

# Initial step size in the normalized [0,10] parameter space.
# 2.0 = 20% of the full range.  Verified working with warm-start init.
# Do not reduce below ~1.5: a small sigma causes the covariance matrix to
# contract prematurely and can produce NaN/Inf parameters that crash the
# C-level SAXS objective function.
DEFAULT_SIGMA0 = 2.0

# Multiplier that converts the user-facing niter (BH outer steps) to
# CMA-ES max function evaluations.  BH with niter=20 and Nelder-Mead
# inner minimization uses roughly 20 * 150 ≈ 3000 evals for a ~50-param
# problem.  200 * niter gives a comparable budget.
FEVALS_PER_NITER = 200


class SolverCMA:
    """CMA-ES solver wrapping the `cma` package.

    Parameters
    ----------
    optimizer : BasicOptimizer
        Fully constructed optimizer that provides `minima_callback` and
        `accept_test`.
    sigma0 : float, optional
        Initial step size in normalized [0,10] space.  Default 2.0.
    """

    def __init__(self, optimizer, sigma0=DEFAULT_SIGMA0):
        self.optimizer = optimizer
        self.sigma0 = sigma0

    def minimize(self, objective, init_params, niter=100, seed=1234,
                 bounds=None, narrow_bounds=False, show_history=False):
        """Run CMA-ES minimization.

        Parameters
        ----------
        objective : callable
            Objective function f(x) → scalar (already wrapped by
            BasicOptimizer.objective_func_wrapper).
        init_params : ndarray
            Initial parameter vector in normalized [0,10] space.
        niter : int
            Controls the evaluation budget: max_fevals = niter * FEVALS_PER_NITER.
            Default 100 (→ 20,000 evaluations).
        seed : int
            RNG seed for CMA-ES.
        bounds : ndarray of shape (n, 2), optional
            Per-parameter [lower, upper] bounds in normalized space.
            If None, defaults to [0, 10] for every parameter.
        narrow_bounds : bool
            If True and bounds is None, restrict to
            [init_params ± NARROW_BOUNDS_ALLOW].
        show_history : bool
            Unused (kept for API parity with SolverBH).

        Returns
        -------
        scipy.optimize.OptimizeResult
            `.x`   — best parameter vector found
            `.fun` — objective value at best x
            `.nit` — number of CMA-ES generations
            `.nfev`— total function evaluations
        """
        import cma

        n = len(init_params)

        if narrow_bounds and bounds is None:
            lower = init_params - NARROW_BOUNDS_ALLOW
            upper = init_params + NARROW_BOUNDS_ALLOW
            bounds = np.array([lower, upper]).T

        if bounds is not None:
            lower_bounds = bounds[:, 0].tolist()
            upper_bounds = bounds[:, 1].tolist()
        else:
            lower_bounds = [0.0] * n
            upper_bounds = [10.0] * n

        max_fevals = niter * FEVALS_PER_NITER

        opts = cma.CMAOptions()
        opts['bounds'] = [lower_bounds, upper_bounds]
        opts['maxfevals'] = max_fevals
        opts['seed'] = seed
        opts['verbose'] = -9      # silent — logging handled by optimizer

        es = cma.CMAEvolutionStrategy(init_params.tolist(), self.sigma0, opts)

        minima_callback = self.optimizer.minima_callback

        best_fv = np.inf
        best_x = init_params.copy()

        while not es.stop():
            solutions = es.ask()
            fitnesses = [objective(np.array(x)) for x in solutions]
            es.tell(solutions, fitnesses)

            gen_best_idx = int(np.argmin(fitnesses))
            gen_best_fv = fitnesses[gen_best_idx]
            gen_best_x = np.array(solutions[gen_best_idx])

            if gen_best_fv < best_fv:
                best_fv = gen_best_fv
                best_x = gen_best_x.copy()
                minima_callback(best_x, best_fv, True)

            # Cooperative stop: check the stop signal every generation, not just
            # on improvement.  Without this, a converged CMA run (no new best)
            # never calls minima_callback, so request_stop() / Terminate button
            # has no effect until the ctypes KI injection fires — which can fail
            # if pycma is inside a C extension holding the GIL.  This makes the
            # dashboard hang at "Status: Terminating..." indefinitely.
            # (molass-library#170)
            if (getattr(self.optimizer, '_stop_event', None) is not None
                    and self.optimizer._stop_event.is_set()):
                break

        r = es.result
        return OptimizeResult(
            x=np.array(r.xbest),
            fun=float(r.fbest),
            nit=int(r.iterations),
            nfev=int(r.evaluations),
            message="CMA-ES stopped: " + str(es.stop()),
            success=True,
        )
