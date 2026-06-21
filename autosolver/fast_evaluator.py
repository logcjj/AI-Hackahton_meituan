from __future__ import annotations

from autosolver.models import EvalResult, ensure_candidate_list


def fast_evaluate(solution, instance) -> EvalResult:
    per_order_p = {order.id: 0.0 for order in instance.orders}
    total_score = 0.0
    violations: list[str] = []
    seen_pairs: set[tuple[object, object]] = set()
    for candidate in ensure_candidate_list(solution):
        rider_id = candidate.rider.id
        for order_id in candidate.order_ids:
            pair = (order_id, rider_id)
            if pair in seen_pairs:
                violations.append(f'duplicate assignment {order_id}/{rider_id}')
            seen_pairs.add(pair)
            previous = per_order_p.get(order_id, 0.0)
            per_order_p[order_id] = 1 - (1 - previous) * (1 - candidate.probability)
        total_score += candidate.probability * candidate.score
    return EvalResult(feasible=not violations, expected_accepts=sum(per_order_p.values()), total_score=total_score, per_order_p=per_order_p, violations=violations)
