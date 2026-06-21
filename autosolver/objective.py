from __future__ import annotations

from autosolver.models import EvalResult


def objective(result: EvalResult, instance) -> float:
    if not result.feasible:
        return float('-inf')
    weight_accepts = instance.weights.expected_accepts
    weight_score = instance.weights.score
    if instance.score_direction == 'reward':
        return weight_accepts * result.expected_accepts + weight_score * result.total_score
    return weight_accepts * result.expected_accepts - weight_score * result.total_score


def better(a: EvalResult, b: EvalResult, instance) -> bool:
    return objective(a, instance) > objective(b, instance)


def marginal_objective_gain(candidate, state, instance) -> float:
    before = state.cached_objective
    after = state.simulate_apply(candidate)
    return after - before
