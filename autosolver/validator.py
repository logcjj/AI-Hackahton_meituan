from __future__ import annotations


def _overlaps(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return max(a[0], b[0]) < min(a[1], b[1])


def validate(output, instance):
    violations = []
    known_orders = {order.id for order in instance.orders}
    known_riders = {rider.id for rider in instance.riders}
    order_by_id = {order.id: order for order in instance.orders}
    assigned_orders = set()
    seen_pairs = set()
    rider_intervals: dict[object, list[tuple[float, float, object, bool]]] = {}

    for assignment in output.get('assignments', []):
        order_id = assignment.get('order_id')
        is_bundle = bool(assignment.get('is_bundle', False))
        if order_id not in known_orders:
            violations.append(f'unknown order {order_id}')
        if order_id in assigned_orders:
            violations.append(f'duplicate order output {order_id}')
        assigned_orders.add(order_id)
        order = order_by_id.get(order_id)
        interval = (order.ready_time, order.due_time) if order is not None else None
        for rider_id in assignment.get('rider_ids', []):
            if rider_id not in known_riders:
                violations.append(f'unknown rider {rider_id}')
            pair = (order_id, rider_id)
            if pair in seen_pairs:
                violations.append(f'duplicate pair {order_id}/{rider_id}')
            seen_pairs.add(pair)
            if interval is not None:
                for start, end, busy_order_id, busy_is_bundle in rider_intervals.get(rider_id, []):
                    same_bundle_projection = is_bundle and busy_is_bundle
                    if not same_bundle_projection and _overlaps(interval, (start, end)):
                        violations.append(f'rider conflict {rider_id}: {busy_order_id}/{order_id}')
                rider_intervals.setdefault(rider_id, []).append((interval[0], interval[1], order_id, is_bundle))

    rejected = output.get('rejected', [])
    for order_id in rejected:
        if order_id not in known_orders:
            violations.append(f'unknown rejected order {order_id}')
        if order_id in assigned_orders:
            violations.append(f'order both assigned and rejected {order_id}')

    covered = assigned_orders | set(rejected)
    missing = known_orders - covered
    if missing:
        violations.append(f'missing orders {sorted(missing)}')
    return violations
