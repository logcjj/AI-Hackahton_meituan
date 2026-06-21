from __future__ import annotations

import itertools
import time

from autosolver.fast_evaluator import fast_evaluate
from autosolver.greedy import greedy_marginal
from autosolver.objective import better
from autosolver.state import SolverState


def _compatible_subset(subset, instance) -> bool:
    state = SolverState(instance)
    for candidate in subset:
        if not state.rider_compatible(candidate):
            return False
        state.apply(candidate)
    return True


def solve_columns(candidates, instance, time_budget=1.0):
    deadline = time.monotonic() + time_budget
    candidates = list(candidates)
    greedy = greedy_marginal(candidates, instance, time_budget=max(0.01, min(0.2, time_budget)))
    best = greedy
    best_eval = fast_evaluate(best, instance)
    if len(candidates) > 22:
        return best
    max_size = min(len(instance.orders) + len(instance.riders), len(candidates), 8)
    for size in range(1, max_size + 1):
        if time.monotonic() >= deadline:
            break
        for subset in itertools.combinations(candidates, size):
            if time.monotonic() >= deadline:
                break
            if not _compatible_subset(subset, instance):
                continue
            eval_result = fast_evaluate(subset, instance)
            if better(eval_result, best_eval, instance):
                best = list(subset)
                best_eval = eval_result
    return best
