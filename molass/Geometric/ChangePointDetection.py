"""
    Geometric.ChangePointDetection.py

    A minimal, dependency-free replacement for the ``ruptures.Dynp(model="l1"|"l2")``
    subset actually used by molass.

    `ruptures` ships compiled Cython extensions (for its Pelt/KernelCPD algorithms),
    but its exact `Dynp` estimator with the "l1"/"l2" costs is pure Python/numpy
    (see github.com/deepcharles/ruptures, src/ruptures/detection/dynp.py and
    src/ruptures/costs/costl1.py, costl2.py). Since `ruptures` currently lacks
    prebuilt wheels for the newest Python versions on some platforms, installing
    it can force a from-source build that requires a C++ compiler. Vendoring the
    small pure-Python algorithm removes that hard dependency entirely.

    Ported from ruptures (BSD-2-Clause), commit as of 2026-09.

    Copyright (c) 2026, SAXS Team, KEK-PF
"""
from functools import lru_cache
from math import ceil
import numpy as np


class _CostL2:
    min_size = 1

    def fit(self, signal):
        self.signal = signal
        return self

    def error(self, start, end):
        return self.signal[start:end].var(axis=0).sum() * (end - start)


class _CostL1:
    min_size = 2

    def fit(self, signal):
        self.signal = signal
        return self

    def error(self, start, end):
        sub = self.signal[start:end]
        med = np.median(sub, axis=0)
        return np.abs(sub - med).sum()


_COST_FACTORY = {"l1": _CostL1, "l2": _CostL2}


def _sanity_check(n_samples, n_bkps, jump, min_size):
    """True if some breakpoint configuration is possible for these parameters."""
    n_adm_bkps = n_samples // jump
    if n_bkps > n_adm_bkps:
        return False
    if n_bkps * ceil(min_size / jump) * jump + min_size > n_samples:
        return False
    return True


class Dynp:
    """Exact change-point detection via dynamic programming.

    Drop-in replacement for ``ruptures.Dynp(model="l1"|"l2")`` covering only the
    options molass actually uses (``.fit(signal).predict(n_bkps=...)``).
    """

    def __init__(self, model="l2", min_size=2, jump=5):
        self.cost = _COST_FACTORY[model]()
        self.min_size = max(min_size, self.cost.min_size)
        self.jump = jump
        self.n_samples = None

    def fit(self, signal):
        signal = np.asarray(signal, dtype=float)
        if signal.ndim == 1:
            signal = signal.reshape(-1, 1)
        self._seg = lru_cache(maxsize=None)(self._seg_impl)
        self.cost.fit(signal)
        self.n_samples = signal.shape[0]
        return self

    def _seg_impl(self, start, end, n_bkps):
        """Optimal partition of signal[start:end] into n_bkps+1 segments."""
        jump, min_size = self.jump, self.min_size
        if n_bkps == 0:
            return {(start, end): self.cost.error(start, end)}

        admissible_bkps = [
            bkp for bkp in range(start, end, jump)
            if _sanity_check(bkp - start, n_bkps - 1, jump, min_size) and end - bkp >= min_size
        ]
        if not admissible_bkps:
            raise ValueError(
                f"No admissible last breakpoints for start={start}, end={end}, n_bkps={n_bkps}."
            )

        sub_problems = []
        for bkp in admissible_bkps:
            left = self._seg(start, bkp, n_bkps - 1)
            right_cost = self._seg(bkp, end, 0)[(bkp, end)]
            merged = dict(left)
            merged[(bkp, end)] = right_cost
            sub_problems.append(merged)

        return min(sub_problems, key=lambda d: sum(d.values()))

    def predict(self, n_bkps):
        if not _sanity_check(self.n_samples, n_bkps, self.jump, self.min_size):
            raise ValueError(
                f"Cannot find {n_bkps} breakpoints with jump={self.jump}, min_size={self.min_size}."
            )
        partition = self._seg(0, self.n_samples, n_bkps)
        return sorted(e for _, e in partition.keys())

    def fit_predict(self, signal, n_bkps):
        return self.fit(signal).predict(n_bkps)
