from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class Weights:
    expected_accepts: float = 1.0
    score: float = 0.5


@dataclass(frozen=True)
class Order:
    id: Any
    pickup: tuple[float, float] = (0.0, 0.0)
    dropoff: tuple[float, float] = (0.0, 0.0)
    ready_time: float = 0.0
    due_time: float = 10.0
    score: float = 10.0


@dataclass(frozen=True)
class Rider:
    id: Any
    start: tuple[float, float] = (0.0, 0.0)


@dataclass
class Instance:
    id: str
    orders: list[Order]
    riders: list[Rider]
    p: Any
    weights: Weights = field(default_factory=Weights)
    score_direction: str = 'reward'
    bundle_pickup_threshold: float = 1.0
    bundle_direction_threshold: float = 45.0
    score_mode: str = 'ACCEPTED_ORDER'

    def __post_init__(self) -> None:
        self.p = [[float(value) for value in row] for row in self.p]
        self.order_index = {order.id: idx for idx, order in enumerate(self.orders)}
        self.rider_index = {rider.id: idx for idx, rider in enumerate(self.riders)}

    def order_pos(self, order_id: Any) -> int:
        if order_id in self.order_index:
            return self.order_index[order_id]
        if isinstance(order_id, int) and 0 <= order_id < len(self.orders):
            return order_id
        raise KeyError(order_id)


@dataclass
class AssignmentCandidate:
    order_ids: list[Any]
    rider: Rider
    probability: float
    score: float
    route: list[Any] = field(default_factory=list)
    is_bundle: bool = False

    @property
    def expected_accepts(self) -> float:
        return self.probability * len(self.order_ids)


@dataclass
class EvalResult:
    feasible: bool
    expected_accepts: float
    total_score: float
    per_order_p: dict[Any, float]
    violations: list[str] = field(default_factory=list)


def ensure_candidate_list(solution: Iterable[AssignmentCandidate] | None) -> list[AssignmentCandidate]:
    return list(solution or [])
