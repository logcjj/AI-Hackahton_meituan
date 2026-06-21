from __future__ import annotations

from collections import defaultdict

from autosolver.models import ensure_candidate_list


def format_solution(solution, instance, mode='submit'):
    by_order = defaultdict(list)
    bundle_orders = set()
    for candidate in ensure_candidate_list(solution):
        for order_id in candidate.order_ids:
            by_order[order_id].append(candidate.rider.id)
            if candidate.is_bundle:
                bundle_orders.add(order_id)
    assignments = []
    for order in instance.orders:
        rider_ids = by_order.get(order.id, [])
        if not rider_ids:
            continue
        assignments.append({
            'order_id': order.id,
            'rider_ids': rider_ids,
            'is_multi_dispatch': len(rider_ids) > 1,
            'is_bundle': order.id in bundle_orders,
        })
    assigned = {item['order_id'] for item in assignments}
    output = {'assignments': assignments, 'rejected': [order.id for order in instance.orders if order.id not in assigned]}
    if mode == 'debug':
        output['debug'] = {'n_assignments': len(assignments)}
    return output
