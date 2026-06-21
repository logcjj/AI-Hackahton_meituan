from __future__ import annotations


def choose_strategy(instance, time_budget=10.0):
    n_orders = len(instance.orders)
    n_riders = len(instance.riders)
    if time_budget < 2 or n_orders > 150 or n_orders * max(1, n_riders) > 5000:
        return 'greedy_only'
    if n_orders <= 12 and n_riders <= 20 and time_budget >= 3:
        return 'column_then_lns'
    return 'greedy_lns_light'
