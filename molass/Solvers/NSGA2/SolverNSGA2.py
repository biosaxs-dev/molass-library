"""
    molass.Solvers.NSGA2.SolverNSGA2

    Multi-objective NSGA-II solver wrapping pymoo.

    Instead of minimizing the synthesized scalar `fv`, this solver treats the 7
    raw score components as separate objectives and lets NSGA-II maintain a
    Pareto front across all of them simultaneously.

    After the run, `synthesize()` is applied to each Pareto-optimal solution to
    pick the best — but the search itself never saw the synthesized scalar.

    This sidesteps the risk that `synthesize()`'s weighting creates a misleading
    landscape that causes BH and CMA-ES to converge to wrong basins.

    Interface matches SolverCMA / SolverDE so it can be wired into
    BasicOptimizer.solve() with method='nsga2'.

    Parameters are in the normalized [0, 10] space used throughout the
    molass-legacy optimizer infrastructure.

    Copyright (c) 2026, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.optimize import OptimizeResult

# 7 score components (indices into the score_list returned by objective_func
# with return_full=True):
#   0  XR_2D_fitting
#   1  XR_LRF_residual
#   2  UV_2D_fitting
#   3  UV_LRF_residual
#   4  Guinier_deviation
#   5  Kratky_smoothness
#   6  SEC_conformance
N_OBJ = 7

# Index of negative_penalty in the full score_list_with_penalties (after the 7 major scores).
# score_list_with_penalties order (from get_score_names):
#   7 = mapping_penalty, 8 = negative_penalty, 9 = baseline_penalty, ...
# We pass negative_penalty as an inequality constraint G ≤ 0 so NSGA-II penalises
# solutions with negative scattering profiles, matching BH behaviour.
# The constraint value is: G = negative_penalty (must be 0 to satisfy).
_NEG_PENALTY_IDX = 8   # index 8 in score_list_with_penalties

# Evaluation budget multiplier: max_fevals = niter * FEVALS_PER_NITER
FEVALS_PER_NITER = 200


class SolverNSGA2:
    """NSGA-II solver using pymoo.

    Treats the 7 raw score components as separate objectives.  After the run,
    applies `synthesize()` to each Pareto member and returns the best as if it
    were a single-objective result — so RunInfo / callback.txt / load_best()
    all work unchanged.

    Parameters
    ----------
    optimizer : BasicOptimizer
        Fully constructed optimizer with `objective_func` and `minima_callback`.
    pop_size : int
        NSGA-II population size.  Default 100.
    """

    def __init__(self, optimizer, pop_size=100):
        self.optimizer = optimizer
        self.pop_size = pop_size

    def minimize(self, objective, init_params, niter=100, seed=1234,
                 bounds=None, narrow_bounds=False, show_history=False):
        """Run NSGA-II minimization on the 7 raw score components.

        Parameters
        ----------
        objective : callable
            The synthesized scalar objective (used only for minima_callback
            and as fallback).  NOT used for the NSGA-II search itself.
        init_params : ndarray
            Initial parameter vector in normalized [0, 10] space.
        niter : int
            Budget: max_fevals = niter * FEVALS_PER_NITER.
        seed : int
            RNG seed.
        bounds, narrow_bounds, show_history
            Same API as SolverBH / SolverCMA (bounds used; others ignored).

        Returns
        -------
        scipy.optimize.OptimizeResult
            `.x`   — best parameter vector (lowest synthesize() across Pareto front)
            `.fun` — synthesized fv at that point
            `.nit` — NSGA-II generations completed
            `.nfev`— total function evaluations
        """
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.core.problem import ElementwiseProblem
        from pymoo.core.termination import NoTermination
        from pymoo.optimize import minimize as pymoo_minimize
        from molass_legacy.Optimizer.FvSynthesizer import synthesize

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

        # ── multi-objective wrapper ──────────────────────────────────────────
        # objective_func(real_params, return_full=True) returns
        # (fv, score_list_with_penalties, *matrices)
        # score_list_with_penalties[0:N_OBJ] are the 7 raw scores.
        _objective_func = self.optimizer.objective_func
        _to_real = self.optimizer.to_real_params
        _lock = self.optimizer._objective_lock

        class _MultiObjProblem(ElementwiseProblem):
            def __init__(self_inner):
                # n_ieq_constr=1: negative_penalty ≤ 0 (satisfied when = 0)
                # This prevents NSGA-II from exploring solutions with negative
                # scattering profiles, matching the behaviour of BH (which
                # adds negative_penalty directly to fv).
                super().__init__(n_var=n, n_obj=N_OBJ, n_ieq_constr=1, xl=xl, xu=xu)

            def _evaluate(self_inner, x, out, *args, **kwargs):
                real_params = _to_real(x)
                with _lock:
                    result = _objective_func(real_params, return_full=True)
                if isinstance(result, tuple) and len(result) >= 2:
                    score_list = np.array(result[1], dtype=float)
                    # 7 major scores as objectives
                    F = score_list[:N_OBJ].copy()
                    F = np.where(np.isnan(F), 1e6, F)
                    out["F"] = F
                    # negative_penalty as inequality constraint G ≤ 0
                    neg_penalty = score_list[_NEG_PENALTY_IDX] if len(score_list) > _NEG_PENALTY_IDX else 0.0
                    out["G"] = np.array([float(neg_penalty)])
                else:
                    fv = float(result) if not isinstance(result, tuple) else float(result[0])
                    out["F"] = np.full(N_OBJ, fv)
                    out["G"] = np.array([0.0])

        problem = _MultiObjProblem()

        # Warm-start: inject init_params as first member of initial population
        from pymoo.operators.sampling.rnd import FloatRandomSampling

        class _WarmStartSampling(FloatRandomSampling):
            def _do(self_inner, problem, n_samples, **kwargs):
                rng = np.random.default_rng(seed)
                X = rng.uniform(xl, xu, size=(n_samples, n))
                X[0] = np.clip(init_params, xl, xu)
                return X

        max_fevals = niter * FEVALS_PER_NITER
        max_gen = max(1, max_fevals // self.pop_size)

        algorithm = NSGA2(
            pop_size=self.pop_size,
            sampling=_WarmStartSampling(),
        )

        minima_callback = self.optimizer.minima_callback
        stop_event = getattr(self.optimizer, '_stop_event', None)

        best_fv = np.inf
        best_x = init_params.copy()
        n_gen = 0
        n_fev = 0

        # Run NSGA-II generation by generation using ask-and-tell
        from pymoo.core.termination import NoTermination
        from pymoo.problems.static import StaticProblem

        algorithm = algorithm.setup(problem, termination=NoTermination(),
                                    seed=seed, verbose=False)

        while algorithm.has_next() and n_gen < max_gen:
            # ask → evaluate → tell
            pop = algorithm.ask()
            # Evaluate each individual (ElementwiseProblem evaluates one at a time)
            algorithm.evaluator.eval(problem, pop)
            algorithm.tell(infills=pop)
            n_gen += 1
            n_fev += len(pop)

            # Find best synthesized fv on current Pareto front (feasible solutions only)
            pareto_F = algorithm.result().F if n_gen == max_gen else None
            pareto_G = algorithm.result().G if n_gen == max_gen else None
            if pareto_F is None:
                # Mid-run: use current population's non-dominated front
                try:
                    from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
                    nds = NonDominatedSorting()
                    all_F = pop.get("F")
                    all_G = pop.get("G")
                    # Consider only feasible individuals (G ≤ 0) for Pareto ranking
                    feasible = np.all(all_G <= 0, axis=1)
                    if np.any(feasible):
                        fronts = nds.do(all_F[feasible])
                        fidx = np.where(feasible)[0][fronts[0]]
                    else:
                        # No feasible solution yet — fall back to full population
                        fronts = nds.do(all_F)
                        fidx = fronts[0]
                    front0_F = all_F[fidx]
                    front0_G = all_G[fidx]
                    front0_X = pop.get("X")[fidx]
                except Exception:
                    front0_F = pop.get("F")
                    front0_G = pop.get("G")
                    front0_X = pop.get("X")
            else:
                front0_F = pareto_F
                front0_G = pareto_G if pareto_G is not None else np.zeros((len(pareto_F), 1))
                front0_X = algorithm.result().X

            # synthesize() on the 7 scores + add negative_penalty (G[:,0]) so
            # the callback fv is on the same scale as BH's objective.
            sv_arr = np.array([
                synthesize(f, positive_elevate=3) + max(0.0, float(g[0]))
                for f, g in zip(front0_F, front0_G)
            ])
            best_idx = int(np.argmin(sv_arr))
            gen_best_fv = float(sv_arr[best_idx])
            gen_best_x = front0_X[best_idx]

            if gen_best_fv < best_fv:
                best_fv = gen_best_fv
                best_x = gen_best_x.copy()
                minima_callback(best_x, best_fv, True)

            # Cooperative stop
            if stop_event is not None and stop_event.is_set():
                break

        return OptimizeResult(
            x=best_x,
            fun=best_fv,
            nit=n_gen,
            nfev=n_fev,
            message="NSGA-II finished: %d gen, %d fevals" % (n_gen, n_fev),
            success=True,
        )
