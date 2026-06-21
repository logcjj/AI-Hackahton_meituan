from __future__ import annotations

import random
import time

from autosolver.fast_evaluator import fast_evaluate
from autosolver.greedy import greedy_marginal
from autosolver.objective import better
from autosolver.utils.seed import get_seed


def _candidate_key(candidate):
    return tuple(candidate.order_ids), candidate.rider.id, candidate.is_bundle


def improve(instance, candidates, baseline, time_budget=1.0, trace=None):
    deadline = time.monotonic() + max(0.0, time_budget)
    rng = random.Random(get_seed(instance, 'lns'))
    best = list(baseline or [])
    best_eval = fast_evaluate(best, instance)
    if trace is not None:
        trace.add('lns_start', baseline_size=len(best), candidate_count=len(candidates))

    if not candidates or time.monotonic() >= deadline:
        return best

    iterations = 0
    while time.monotonic() < deadline and iterations < 20:
        iterations += 1
        current = list(best)
        if current:
            destroy_count = max(1, len(current) // 3)
            remove_keys = {_candidate_key(candidate) for candidate in rng.sample(current, min(destroy_count, len(current)))}
            partial = [candidate for candidate in current if _candidate_key(candidate) not in remove_keys]
        else:
            partial = []
        used_keys = {_candidate_key(candidate) for candidate in partial}
        repair_pool = [candidate for candidate in candidates if _candidate_key(candidate) not in used_keys]
        repaired = greedy_marginal(repair_pool, instance, time_budget=max(0.01, min(0.05, deadline - time.monotonic())), initial_solution=partial)
        repaired_eval = fast_evaluate(repaired, instance)
        if better(repaired_eval, best_eval, instance):
            best = repaired
            best_eval = repaired_eval
            if trace is not None:
                trace.add('lns_improved', iteration=iterations, expected_accepts=best_eval.expected_accepts, total_score=best_eval.total_score)

    if trace is not None:
        trace.add('lns_done', iterations=iterations, final_size=len(best))
    return best
