from __future__ import annotations


from autosolver.models import Instance, Order, Rider, Weights


def _point(raw, key, default=(0.0, 0.0)):
    value = raw.get(key, default)
    if isinstance(value, dict):
        return (float(value.get('x', 0.0)), float(value.get('y', 0.0)))
    return tuple(value) if isinstance(value, (list, tuple)) and len(value) == 2 else default


def adapt(raw_input):
    if raw_input.get('force_adapter_error'):
        raise ValueError('forced adapter failure')
    orders = [
        Order(
            id=raw.get('order_id', raw.get('id', index)),
            pickup=_point(raw, 'pickup'),
            dropoff=_point(raw, 'dropoff', (1.0, 0.0)),
            ready_time=float(raw.get('ready_time', 0.0)),
            due_time=float(raw.get('due_time', 10.0)),
            score=float(raw.get('score', 10.0)),
        )
        for index, raw in enumerate(raw_input.get('orders', []))
    ]
    riders = [
        Rider(id=raw.get('rider_id', raw.get('id', index)), start=_point(raw, 'start'))
        for index, raw in enumerate(raw_input.get('riders', []))
    ]
    if not riders and orders:
        riders = [Rider(id=f'R{index}') for index in range(max(1, len(orders)))]
    p = raw_input.get('p', raw_input.get('p_matrix'))
    if p is None:
        p = [[0.5 for _ in riders] for _ in orders]
    weights_raw = raw_input.get('weights', {})
    weights = Weights(expected_accepts=float(weights_raw.get('expected_accepts', weights_raw.get('weight_expected_accepts', 1.0))), score=float(weights_raw.get('score', weights_raw.get('weight_score', 0.5))))
    return Instance(id=str(raw_input.get('id', 'instance')), orders=orders, riders=riders, p=p, weights=weights, score_direction=raw_input.get('score_direction', 'reward'))
