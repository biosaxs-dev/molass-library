"""
    molass.Solvers.BH.SolverBH

    Copyright (c) 2024-2026, SAXS Team, KEK-PF
"""
import numpy as np
from .BasinHopping import BasinHopping

NARROW_BOUNDS_ALLOW = 1.0

class SolverBH:
    def __init__(self, optimizer):
        self.bh_impl = BasinHopping()
        self.optimizer = optimizer

    def minimize(self, objective, init_params, niter=100, seed=1234, bounds=None, narrow_bounds=False, show_history=False):

        if narrow_bounds:
            lower = init_params - NARROW_BOUNDS_ALLOW
            upper = init_params + NARROW_BOUNDS_ALLOW
            bounds = np.array([lower, upper]).T

        minimizer_kwargs = dict(method='Nelder-Mead', bounds=bounds)

        minima_callback = self.optimizer.minima_callback
        accept_test = self.optimizer.accept_test

        result = self.bh_impl.minimize(objective, init_params, niter=niter, seed=seed,
                                callback=minima_callback,
                                accept_test=accept_test,
                                minimizer_kwargs=minimizer_kwargs,
                                custom=show_history)

        if show_history:
            self.bh_impl.show_history(self)

        return result

    def show_history(self, caller):
        self.bh_impl.show_history(caller)
