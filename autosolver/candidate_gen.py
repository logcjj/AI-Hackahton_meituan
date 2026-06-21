from __future__ import annotations

import itertools
import math
import time


from autosolver.models import AssignmentCandidate

TOP_K_RIDERS_PER_ORDER = 8
MIN_ACCEPT_PROB = 0.05
MAX_BUNDLE_SIZE = 2
MAX_CANDIDATES_TOTAL = 5000


def distance(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def feasible_single(order, rider, instance) -> bool:
    return order.ready_time <= order.due_time


def make_single_candidate(order, rider, instance) -> AssignmentCandidate:
    order_idx = instance.order_pos(order.id)
    rider_idx = instance.rider_index[rider.id]
    probability = float(instance.p[order_idx][rider_idx])
    return AssignmentCandidate(order_ids=[order.id], rider=rider, probability=probability, score=order.score, route=[order.id], is_bundle=False)


def generate_bundle_groups(instance, max_size=MAX_BUNDLE_SIZE, max_pickup_distance=1.0, max_drop_angle=45.0):
    if max_size < 2:
        return []
    groups = []
    for group in itertools.combinations(instance.orders, 2):
        if distance(group[0].pickup, group[1].pickup) <= max_pickup_distance:
            groups.append(list(group))
    return groups


def find_best_feasible_route(group, rider, instance):
    if all(order.ready_time <= order.due_time for order in group):
        return [order.id for order in group]
    return None


def estimate_bundle_accept_prob(rider, group, best_route, instance) -> float:
    rider_idx = instance.rider_index[rider.id]
    base_p = min(float(instance.p[instance.order_pos(order.id)][rider_idx]) for order in group)
    detour_factor = 0.95
    return base_p * detour_factor


def make_bundle_candidate(group, rider, best_route, p, instance) -> AssignmentCandidate:
    return AssignmentCandidate(order_ids=[order.id for order in group], rider=rider, probability=float(p), score=sum(order.score for order in group), route=list(best_route), is_bundle=True)


def _top_indices_desc(values, k):
    if len(values) == 0 or k <= 0:
        return []
    return sorted(range(len(values)), key=lambda index: -values[index])[:k]


def _truncate(candidates, limit):
    return candidates[:limit]


def generate_candidates(instance, time_budget=1.0):
    deadline = time.monotonic() + time_budget
    candidates = []
    p_matrix = instance.p
    if len(instance.orders) == 0 or len(instance.riders) == 0:
        return []

    for order_idx, order in enumerate(instance.orders):
        for rider_idx in _top_indices_desc(p_matrix[order_idx], TOP_K_RIDERS_PER_ORDER):
            if p_matrix[order_idx][rider_idx] < MIN_ACCEPT_PROB:
                continue
            rider = instance.riders[rider_idx]
            if feasible_single(order, rider, instance):
                candidates.append(make_single_candidate(order, rider, instance))

    if time.monotonic() > deadline:
        return _truncate(candidates, MAX_CANDIDATES_TOTAL)

    for group in generate_bundle_groups(instance, max_size=MAX_BUNDLE_SIZE, max_pickup_distance=instance.bundle_pickup_threshold, max_drop_angle=instance.bundle_direction_threshold):
        if time.monotonic() > deadline:
            break
        order_positions = [instance.order_pos(order.id) for order in group]
        bundle_base_p = [min(p_matrix[order_pos][rider_idx] for order_pos in order_positions) for rider_idx in range(len(instance.riders))]
        top_k_for_bundle = TOP_K_RIDERS_PER_ORDER * 2
        for rider_idx in _top_indices_desc(bundle_base_p, top_k_for_bundle):
            if bundle_base_p[rider_idx] < MIN_ACCEPT_PROB:
                continue
            rider = instance.riders[rider_idx]
            best_route = find_best_feasible_route(group, rider, instance)
            if best_route is None:
                continue
            probability = estimate_bundle_accept_prob(rider, group, best_route, instance)
            if probability < MIN_ACCEPT_PROB:
                continue
            candidates.append(make_bundle_candidate(group, rider, best_route, probability, instance))

    return _truncate(candidates, MAX_CANDIDATES_TOTAL)
