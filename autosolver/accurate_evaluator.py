from __future__ import annotations

import random

from autosolver.fast_evaluator import fast_evaluate
from autosolver.models import EvalResult, ensure_candidate_list
from autosolver.utils.seed import get_seed


def accurate_evaluate(solution, instance, n_simulations=500):
    candidates = ensure_candidate_list(solution)
    if n_simulations <= 0 or not candidates:
        return fast_evaluate(candidates, instance)
    rng = random.Random(get_seed(instance, 'accurate_evaluator'))
    order_hits = {order.id: 0 for order in instance.orders}
    total_score = 0.0
    for _ in range(n_simulations):
        accepted_orders = set()
        score = 0.0
        for candidate in candidates:
            if rng.random() <= candidate.probability:
                for order_id in candidate.order_ids:
                    accepted_orders.add(order_id)
                score += candidate.score
        for order_id in accepted_orders:
            order_hits[order_id] += 1
        total_score += score
    per_order_p = {order_id: hits / n_simulations for order_id, hits in order_hits.items()}
    closed_form = fast_evaluate(candidates, instance)
    return EvalResult(
        feasible=closed_form.feasible,
        expected_accepts=sum(per_order_p.values()),
        total_score=total_score / n_simulations,
        per_order_p=per_order_p,
        violations=list(closed_form.violations),
    )
