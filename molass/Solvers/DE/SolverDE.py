"""
    molass.Solvers.DE.SolverDE

    Differential Evolution solver wrapping pymoo.

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

    With the default pop_size=None the population is sized automatically as
    max(20, 5 * n_var) — i.e. 150 for a 30-param problem, 250 for 50 params.

    Unlike CMA-ES (pycma), pymoo's DE is pure Python so it does NOT trigger
    the ProactorEventLoop / BLAS C-extension race that caused the molass-library
    #193 async crash.  It is therefore safe to run with in_process=True and
    async_=True.

    Copyright (c) 2026, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.optimize import OptimizeResult

# Evaluation budget multiplier: max_fevals = niter * FEVALS_PER_NITER.
# Matches SolverCMA so niter values are comparable across methods.
FEVALS_PER_NITER = 200


class SolverDE:
    """Differential Evolution solver wrapping pymoo DE.

    Parameters
    ----------
    optimizer : BasicOptimizer
        Fully constructed optimizer that provides ``minima_callback``.
    pop_size : int or None
        Population size.  None → max(20, 5 * n_var) (auto-sized).
    variant : str
        DE variant string understood by pymoo, e.g. ``"DE/rand/1/bin"``.
    CR : float
        Crossover probability (0–1).
    F : float or tuple
        Differential weight (mutation factor).  A tuple ``(F_min, F_max)``
        enables dithering.
    """

    def __init__(self, optimizer, pop_size=None, variant="DE/rand/1/bin",
                 CR=0.5, F=0.5, warm_sigma=1.0):
        self.optimizer = optimizer
        self._pop_size = pop_size
        self.variant = variant
        self.CR = CR
        self.F = F
        self.warm_sigma = warm_sigma

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
        from pymoo.algorithms.soo.nonconvex.de import DE
        from pymoo.core.problem import Problem
        from pymoo.core.termination import NoTermination
        from pymoo.problems.static import StaticProblem

        n = len(init_params)

        # ── bounds ──────────────────────────────────────────────────────────
        if narrow_bounds and bounds is None:
            lower = init_params - 1.0
            upper = init_params + 1.0
            bounds = np.array([lower, upper]).T

        if bounds is not None:
            xl = bounds[:, 0]
            xu = bounds[:, 1]
        else:
            xl = np.zeros(n)
            xu = np.full(n, 10.0)

        # ── population size ──────────────────────────────────────────────────
        pop_size = self._pop_size if self._pop_size is not None else max(20, 5 * n)

        # ── budget ───────────────────────────────────────────────────────────
        max_fevals = niter * FEVALS_PER_NITER
        max_gen = max(1, max_fevals // pop_size)

        # ── set up pymoo problem & algorithm ─────────────────────────────────
        problem = Problem(n_var=n, n_obj=1, xl=xl, xu=xu)

        algorithm = DE(
            pop_size=pop_size,
            variant=self.variant,
            CR=self.CR,
            F=self.F,
            sampling=_WarmStartSampling(init_params, xl, xu, seed=seed,
                                         warm_sigma=self.warm_sigma),
        ).setup(problem, termination=NoTermination(), seed=seed, verbose=False)

        minima_callback = self.optimizer.minima_callback
        stop_event = getattr(self.optimizer, '_stop_event', None)

        best_fv = np.inf
        best_x = init_params.copy()
        n_gen = 0
        n_fev = 0

        while algorithm.has_next() and n_gen < max_gen:
            infills = algorithm.ask()
            X = infills.get("X")

            # evaluate each candidate sequentially (objective is not vectorised)
            F_vals = np.array([float(objective(x)) for x in X], dtype=float)
            n_fev += len(F_vals)

            algorithm.evaluator.eval(
                StaticProblem(problem, F=F_vals[:, None]), infills
            )
            algorithm.tell(infills=infills)
            n_gen += 1

            # track best
            gen_best_idx = int(np.argmin(F_vals))
            gen_best_fv = float(F_vals[gen_best_idx])
            if gen_best_fv < best_fv:
                best_fv = gen_best_fv
                best_x = X[gen_best_idx].copy()
                minima_callback(best_x, best_fv, True)

            # cooperative stop (Terminate button)
            if stop_event is not None and stop_event.is_set():
                break

        # pymoo's algorithm.opt holds the current best population member
        opt = algorithm.opt[0]
        final_x = np.array(opt.X)
        final_fv = float(opt.F[0])

        # use the overall best in case the final population member is not it
        if final_fv > best_fv:
            final_x = best_x
            final_fv = best_fv

        return OptimizeResult(
            x=final_x,
            fun=final_fv,
            nit=n_gen,
            nfev=n_fev,
            message="DE finished after %d generations, %d fevals" % (n_gen, n_fev),
            success=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Warm-start sampling: seed the initial population with init_params + random
# ─────────────────────────────────────────────────────────────────────────────

from pymoo.operators.sampling.rnd import FloatRandomSampling


class _WarmStartSampling(FloatRandomSampling):
    """Initialise the population in a Gaussian cloud around init_params.

    All population members are drawn from N(init_params, warm_sigma²), clipped
    to [xl, xu].  Member 0 is set exactly to init_params so the known best is
    always preserved.

    This guarantees that successive DE jobs (restarted from a previous job's
    best) never produce a population whose best individual is worse than the
    warm-start point — the regression observed when only X[0] was seeded and
    the rest were random.

    ``_do`` must return a plain numpy array — the base ``Sampling.__call__``
    wraps it into a ``Population`` automatically.
    """

    def __init__(self, init_params, xl, xu, seed=1234, warm_sigma=1.0):
        super().__init__()
        self._init = np.clip(init_params, xl, xu)
        self._xl = xl
        self._xu = xu
        self._seed = seed
        self._warm_sigma = warm_sigma

    def _do(self, problem, n_samples, **kwargs):
        rng = np.random.default_rng(self._seed)
        noise = rng.normal(0.0, self._warm_sigma,
                           size=(n_samples, len(self._init)))
        X = np.clip(self._init + noise, self._xl, self._xu)
        X[0] = self._init           # member 0 = exact warm start
        return X
