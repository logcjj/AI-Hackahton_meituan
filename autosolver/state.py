from __future__ import annotations

from autosolver.fast_evaluator import fast_evaluate
from autosolver.objective import objective


class SolverState:
    def __init__(self, instance, solution=None):
        self.instance = instance
        self.solution = list(solution or [])
        self.rider_busy: dict[object, list[tuple[float, float]]] = {}
        self.cached_objective = 0.0
        for candidate in self.solution:
            self._reserve(candidate)
        self._refresh_objective()

    def _candidate_interval(self, candidate) -> tuple[float, float]:
        starts = []
        ends = []
        for order_id in candidate.order_ids:
            order = self.instance.orders[self.instance.order_pos(order_id)]
            starts.append(order.ready_time)
            ends.append(order.due_time)
        return min(starts), max(ends)

    @staticmethod
    def _overlaps(a: tuple[float, float], b: tuple[float, float]) -> bool:
        return max(a[0], b[0]) < min(a[1], b[1])

    def rider_compatible(self, candidate) -> bool:
        interval = self._candidate_interval(candidate)
        return all(not self._overlaps(interval, busy) for busy in self.rider_busy.get(candidate.rider.id, []))

    def _reserve(self, candidate) -> None:
        self.rider_busy.setdefault(candidate.rider.id, []).append(self._candidate_interval(candidate))

    def _refresh_objective(self) -> None:
        self.cached_objective = objective(fast_evaluate(self.solution, self.instance), self.instance)

    def apply(self, candidate) -> None:
        self.solution.append(candidate)
        self._reserve(candidate)
        self._refresh_objective()

    def simulate_apply(self, candidate) -> float:
        if not self.rider_compatible(candidate):
            return float('-inf')
        return objective(fast_evaluate(self.solution + [candidate], self.instance), self.instance)
