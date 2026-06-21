from __future__ import annotations

import time

from autosolver.objective import marginal_objective_gain
from autosolver.state import SolverState


def greedy_marginal(candidates, instance, time_budget=1.0, initial_solution=None):
    deadline = time.monotonic() + time_budget
    state = SolverState(instance, initial_solution)
    remaining = list(candidates)
    while remaining and time.monotonic() < deadline:
        best_candidate = None
        best_gain = 0.0
        best_index = -1
        for index, candidate in enumerate(remaining):
            gain = marginal_objective_gain(candidate, state, instance)
            if gain > best_gain:
                best_gain = gain
                best_candidate = candidate
                best_index = index
        if best_candidate is None or best_gain <= 0:
            break
        state.apply(best_candidate)
        remaining.pop(best_index)
    return state.solution
