from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, replace
from typing import Any, Callable

from web_agent_demo.memory_engine import MemoryRecallBundle, PredictorTrace, rank_algorithms_with_predictor
from web_agent_demo.simulation_engine import (
    CourierState,
    MerchantState,
    OrderState,
    Position,
    SimulationSession,
    SimulationTick,
    TimelineEvent,
    get_scenario,
)


EARTH_METERS_PER_DEGREE = 111_000.0
UNASSIGNED_ORDER_PENALTY = 6_000.0

DEFAULT_ALGORITHMS = (
    "nearest_greedy",
    "cost_greedy",
    "risk_aware_greedy",
    "min_cost_matching",
    "sparse_cover",
    "flow_mcf",
    "autosolver_agent",
)

ALGORITHM_META = {
    "nearest_greedy": ("baseline", "Nearest Greedy"),
    "cost_greedy": ("greedy", "Cost Greedy"),
    "risk_aware_greedy": ("greedy", "Risk-Aware Greedy"),
    "min_cost_matching": ("matching", "Min-Cost Matching"),
    "sparse_cover": ("set-cover", "Sparse Cover"),
    "flow_mcf": ("flow", "Flow MCF"),
    "autosolver_agent": ("agent", "AutoSolver Agent"),
}


@dataclass(frozen=True)
class ScenarioFeatures:
    scenario_id: str
    scene_type: str
    weather: str
    traffic_profile: str
    congestion_level: float
    order_pressure: float
    courier_pressure: float
    active_order_count: int
    courier_count: int
    avg_willingness: float
    burst_active: bool


@dataclass(frozen=True)
class AssignmentDecision:
    order_id: str
    courier_id: str
    merchant_id: str
    pickup_eta_s: float
    delivery_eta_s: float
    eta_s: float
    expected_cost: float
    acceptance_probability: float
    risk_score: float
    rationale: str


@dataclass(frozen=True)
class AlgorithmMetrics:
    coverage_rate: float
    covered_orders: int
    total_orders: int
    avg_eta_s: float
    p95_eta_s: float
    expected_cost: float
    courier_utilization: float
    no_accept_risk: float
    timeout_risk: float
    runtime_ms: float
    relative_to_baseline: dict[str, float]
    score: float


@dataclass(frozen=True)
class AlgorithmResult:
    algorithm_id: str
    algorithm_family: str
    label: str
    status: str
    metrics: AlgorithmMetrics
    assignments: tuple[AssignmentDecision, ...]
    route_overlays: tuple[dict[str, Any], ...]
    reason: str
    risk_flags: tuple[str, ...]
    source_algorithm_id: str | None = None


@dataclass(frozen=True)
class DecisionPoint:
    id: str
    time_s: float
    algorithm_id: str
    title: str
    summary: str
    evidence: dict[str, Any]
    impact: str
    map_focus: tuple[str, ...]


@dataclass(frozen=True)
class CompareRun:
    compare_run_id: str
    session_id: str
    tick_id: str
    started_at: str
    finished_at: str
    time_budget_ms: int
    elapsed_ms: float
    scenario_features: ScenarioFeatures
    algorithms_requested: tuple[str, ...]
    selected_algorithm_id: str
    baseline_algorithm_id: str
    status: str


@dataclass(frozen=True)
class CompareRunResult:
    compare_run: CompareRun
    results: tuple[AlgorithmResult, ...]
    selected: AlgorithmResult
    decision_points: tuple[DecisionPoint, ...]
    memory: MemoryRecallBundle
    predictor: PredictorTrace
    timeline_delta: tuple[TimelineEvent, ...]


@dataclass(frozen=True)
class _AssignmentProfile:
    order: OrderState
    courier: CourierState
    merchant: MerchantState
    pickup_eta_s: float
    delivery_eta_s: float
    eta_s: float
    expected_cost: float
    acceptance_probability: float
    risk_score: float


def run_comparison(
    session: SimulationSession,
    tick: SimulationTick,
    time_budget_ms: int = 10_000,
    algorithms: tuple[str, ...] | list[str] | None = None,
    memory_store: Any | None = None,
    memory_mode: str = "off",
    predictor_mode: str = "fallback",
) -> CompareRunResult:
    requested = tuple(algorithms or DEFAULT_ALGORITHMS)
    if not requested:
        requested = DEFAULT_ALGORITHMS

    direct_requested = tuple(algorithm for algorithm in requested if algorithm != "autosolver_agent")
    if not direct_requested and "autosolver_agent" in requested:
        direct_requested = tuple(algorithm for algorithm in DEFAULT_ALGORITHMS if algorithm != "autosolver_agent")

    features = _scenario_features(session, tick)
    recall = (
        memory_store.recall_similar_context(features, direct_requested, mode=memory_mode)
        if memory_store is not None
        else MemoryRecallBundle.off()
    )
    raw_results = tuple(_evaluate_algorithm(algorithm, tick, features) for algorithm in direct_requested)
    scored_results = _with_relative_scores(raw_results, baseline_algorithm_id="nearest_greedy")
    predictor = rank_algorithms_with_predictor(features, scored_results, recall, mode=predictor_mode)

    if "autosolver_agent" in requested:
        agent_result = _agent_result(scored_results, tick, features, recall, predictor)
        scored_results = (*scored_results, agent_result)
        scored_results = _with_relative_scores(scored_results, baseline_algorithm_id="nearest_greedy")

    selected = _select_result(scored_results, prefer_agent="autosolver_agent" in requested)
    finalized_results = tuple(_with_status(result, "selected" if result.algorithm_id == selected.algorithm_id else "evaluated") for result in scored_results)
    selected = next(result for result in finalized_results if result.algorithm_id == selected.algorithm_id)
    elapsed_ms = round(sum(result.metrics.runtime_ms for result in finalized_results), 3)
    compare_run_id = _stable_id("compare", session.session_id, tick.tick_id, ",".join(requested), len(tick.active_order_ids))
    status = "completed" if elapsed_ms <= time_budget_ms else "partial"
    compare_run = CompareRun(
        compare_run_id=compare_run_id,
        session_id=session.session_id,
        tick_id=tick.tick_id,
        started_at=f"sim:{tick.tick_id}:compare-start",
        finished_at=f"sim:{tick.tick_id}:compare-finish",
        time_budget_ms=int(time_budget_ms),
        elapsed_ms=elapsed_ms,
        scenario_features=features,
        algorithms_requested=requested,
        selected_algorithm_id=selected.algorithm_id,
        baseline_algorithm_id="nearest_greedy",
        status=status,
    )
    result = CompareRunResult(
        compare_run=compare_run,
        results=finalized_results,
        selected=selected,
        decision_points=_decision_points(compare_run, finalized_results, selected),
        memory=recall,
        predictor=predictor,
        timeline_delta=_timeline_delta(compare_run, finalized_results, selected, tick),
    )
    if memory_store is not None and memory_mode == "read-write":
        memory_store.record_compare_result(result)
    return result


def _evaluate_algorithm(algorithm_id: str, tick: SimulationTick, features: ScenarioFeatures) -> AlgorithmResult:
    family, label = ALGORITHM_META.get(algorithm_id, ("unknown", algorithm_id))
    assignments_by_algorithm: dict[str, Callable[[SimulationTick], tuple[AssignmentDecision, ...]]] = {
        "nearest_greedy": _nearest_greedy,
        "cost_greedy": _cost_greedy,
        "risk_aware_greedy": _risk_aware_greedy,
        "min_cost_matching": _min_cost_matching,
        "sparse_cover": _sparse_cover,
        "flow_mcf": _flow_mcf,
    }
    if algorithm_id not in assignments_by_algorithm:
        return _failed_result(algorithm_id, tick, f"Unknown algorithm: {algorithm_id}")

    assignments = assignments_by_algorithm[algorithm_id](tick)
    runtime_ms = _estimated_runtime_ms(algorithm_id, features.active_order_count, features.courier_count)
    metrics = _metrics_for(assignments, tick, runtime_ms)
    return AlgorithmResult(
        algorithm_id=algorithm_id,
        algorithm_family=family,
        label=label,
        status="evaluated",
        metrics=metrics,
        assignments=assignments,
        route_overlays=_route_overlays(assignments, tick),
        reason=_reason_for(algorithm_id, metrics, features),
        risk_flags=_risk_flags(metrics),
    )


def _nearest_greedy(tick: SimulationTick) -> tuple[AssignmentDecision, ...]:
    return _greedy_assign(
        tick,
        order_key=lambda order: (order.created_at_s, order.id),
        candidate_key=lambda profile: (_distance_m(profile.courier.position, profile.merchant.position), profile.order.id, profile.courier.id),
        rationale="nearest available courier",
    )


def _cost_greedy(tick: SimulationTick) -> tuple[AssignmentDecision, ...]:
    return _greedy_assign(
        tick,
        order_key=lambda order: (-order.priority, order.deadline_s, order.id),
        candidate_key=lambda profile: (profile.expected_cost, profile.eta_s, profile.courier.id),
        rationale="lowest expected cost",
    )


def _risk_aware_greedy(tick: SimulationTick) -> tuple[AssignmentDecision, ...]:
    return _assignment_dp(
        tick,
        score_fn=lambda profile: (
            (1.0 - profile.acceptance_probability) * 4_000.0
            + profile.risk_score * 1_250.0
            + profile.eta_s * 0.35
            - _order_urgency(profile.order, tick) * 140.0
        ),
        rationale="risk-adjusted ETA and acceptance",
        skip_penalty_fn=lambda order: UNASSIGNED_ORDER_PENALTY
        * (0.55 + _best_acceptance_probability(order, tick) * 0.62 + _order_urgency(order, tick) * 0.12),
        fallback_sort=lambda profile: (
            (1.0 - profile.acceptance_probability) * 4_000.0
            + profile.risk_score * 1_250.0
            + profile.eta_s * 0.35
            - _order_urgency(profile.order, tick) * 140.0,
            profile.eta_s,
            profile.order.id,
            profile.courier.id,
        ),
    )


def _min_cost_matching(tick: SimulationTick) -> tuple[AssignmentDecision, ...]:
    return _assignment_dp(
        tick,
        score_fn=lambda profile: profile.expected_cost,
        rationale="global min-cost one-to-one matching",
        fallback_sort=lambda profile: (profile.expected_cost, profile.eta_s, profile.order.id, profile.courier.id),
    )


def _sparse_cover(tick: SimulationTick) -> tuple[AssignmentDecision, ...]:
    orders = _active_orders(tick)
    couriers = _available_couriers(tick)
    if not orders or not couriers:
        return ()

    merchant_pressure = {merchant.id: merchant.pressure for merchant in tick.merchants}
    pairs = []
    for order in orders:
        for courier in couriers:
            profile = _assignment_profile(order, courier, tick)
            coverage_value = order.priority * 500.0 + merchant_pressure.get(order.merchant_id, 0.0) * 220.0
            pairs.append((profile.expected_cost + profile.risk_score * 500.0 - coverage_value, profile))
    return _assign_from_sorted_pairs(tick, sorted(pairs, key=lambda item: (item[0], item[1].order.id, item[1].courier.id)), "coverage-first sparse cover")


def _flow_mcf(tick: SimulationTick) -> tuple[AssignmentDecision, ...]:
    return _assignment_dp(
        tick,
        score_fn=lambda profile: profile.expected_cost + profile.risk_score * 650.0 - profile.order.priority * 160.0,
        rationale="flow-style min-cost risk-balanced dispatch",
        fallback_sort=lambda profile: (
            profile.expected_cost + profile.risk_score * 650.0 - profile.order.priority * 160.0,
            profile.eta_s,
            profile.order.id,
            profile.courier.id,
        ),
    )


def _greedy_assign(
    tick: SimulationTick,
    order_key: Callable[[OrderState], tuple[Any, ...]],
    candidate_key: Callable[[_AssignmentProfile], tuple[Any, ...]],
    rationale: str,
) -> tuple[AssignmentDecision, ...]:
    available = {courier.id: courier for courier in _available_couriers(tick)}
    assignments = []
    for order in sorted(_active_orders(tick), key=order_key):
        if not available:
            break
        profiles = [_assignment_profile(order, courier, tick) for courier in available.values()]
        chosen = min(profiles, key=candidate_key)
        assignments.append(_assignment_decision(chosen, rationale))
        available.pop(chosen.courier.id, None)
    return tuple(assignments)


def _assignment_dp(
    tick: SimulationTick,
    score_fn: Callable[[_AssignmentProfile], float],
    rationale: str,
    fallback_sort: Callable[[_AssignmentProfile], tuple[Any, ...]],
    skip_penalty_fn: Callable[[OrderState], float] | None = None,
) -> tuple[AssignmentDecision, ...]:
    orders = tuple(sorted(_active_orders(tick), key=lambda order: (-_order_urgency(order, tick), order.deadline_s, order.id)))
    couriers = _available_couriers(tick)
    if not orders or not couriers:
        return ()
    if len(orders) > 12 or len(couriers) > 18:
        pairs = [(fallback_sort(_assignment_profile(order, courier, tick)), _assignment_profile(order, courier, tick)) for order in orders for courier in couriers]
        return _assign_from_sorted_pairs(tick, sorted(pairs, key=lambda item: item[0]), rationale)

    states: dict[int, tuple[float, tuple[_AssignmentProfile, ...]]] = {0: (0.0, ())}
    full_capacity_mask = (1 << len(couriers)) - 1
    for order in orders:
        next_states: dict[int, tuple[float, tuple[_AssignmentProfile, ...]]] = {}
        for mask, (cost, chosen_profiles) in states.items():
            skip_cost = cost + (skip_penalty_fn(order) if skip_penalty_fn is not None else _unassigned_penalty(order, tick))
            _keep_best(next_states, mask, skip_cost, chosen_profiles)
            if mask == full_capacity_mask:
                continue
            for index, courier in enumerate(couriers):
                courier_bit = 1 << index
                if mask & courier_bit:
                    continue
                profile = _assignment_profile(order, courier, tick)
                _keep_best(next_states, mask | courier_bit, cost + score_fn(profile), (*chosen_profiles, profile))
        states = next_states

    _, best_profiles = min(states.values(), key=lambda item: (item[0], -len(item[1]), tuple(profile.order.id for profile in item[1])))
    return tuple(_assignment_decision(profile, rationale) for profile in best_profiles)


def _keep_best(
    states: dict[int, tuple[float, tuple[_AssignmentProfile, ...]]],
    mask: int,
    cost: float,
    profiles: tuple[_AssignmentProfile, ...],
) -> None:
    current = states.get(mask)
    if current is None or (cost, -len(profiles), tuple(profile.order.id for profile in profiles)) < (
        current[0],
        -len(current[1]),
        tuple(profile.order.id for profile in current[1]),
    ):
        states[mask] = (cost, profiles)


def _assign_from_sorted_pairs(
    tick: SimulationTick,
    sorted_pairs: list[tuple[Any, _AssignmentProfile]],
    rationale: str,
) -> tuple[AssignmentDecision, ...]:
    used_orders: set[str] = set()
    used_couriers: set[str] = set()
    assignments = []
    target = min(len(_active_orders(tick)), len(_available_couriers(tick)))
    for _, profile in sorted_pairs:
        if profile.order.id in used_orders or profile.courier.id in used_couriers:
            continue
        assignments.append(_assignment_decision(profile, rationale))
        used_orders.add(profile.order.id)
        used_couriers.add(profile.courier.id)
        if len(assignments) >= target:
            break
    return tuple(assignments)


def _agent_result(
    results: tuple[AlgorithmResult, ...],
    tick: SimulationTick,
    features: ScenarioFeatures,
    recall: MemoryRecallBundle,
    predictor: PredictorTrace,
) -> AlgorithmResult:
    if not results:
        return _failed_result("autosolver_agent", tick, "No candidate algorithms were available for local critic selection.")
    source = _source_from_predictor(results, predictor) or _select_result(results, prefer_agent=False)
    family, label = ALGORITHM_META["autosolver_agent"]
    metrics = replace(source.metrics, runtime_ms=round(source.metrics.runtime_ms + _estimated_runtime_ms("autosolver_agent", features.active_order_count, features.courier_count), 3))
    reason_parts = [f"{predictor.provider} selected {source.label}"]
    if recall.strategy_memory:
        reason_parts.append(recall.effect_on_ranking)
    else:
        reason_parts.append("No similar memory changed the ranking.")
    return AlgorithmResult(
        algorithm_id="autosolver_agent",
        algorithm_family=family,
        label=label,
        status="evaluated",
        metrics=metrics,
        assignments=source.assignments,
        route_overlays=source.route_overlays,
        reason="; ".join(reason_parts),
        risk_flags=source.risk_flags,
        source_algorithm_id=source.algorithm_id,
    )


def _source_from_predictor(results: tuple[AlgorithmResult, ...], predictor: PredictorTrace) -> AlgorithmResult | None:
    result_by_id = {result.algorithm_id: result for result in results if result.status not in {"failed", "timeout"}}
    for item in predictor.ranked_algorithms:
        algorithm_id = str(item.get("algorithm_id") or "")
        if algorithm_id in result_by_id:
            return result_by_id[algorithm_id]
    return None


def _select_result(results: tuple[AlgorithmResult, ...], prefer_agent: bool) -> AlgorithmResult:
    if prefer_agent:
        for result in results:
            if result.algorithm_id == "autosolver_agent":
                return result
    return max(
        results,
        key=lambda result: (
            result.metrics.coverage_rate,
            result.metrics.score,
            -result.metrics.timeout_risk,
            -result.metrics.no_accept_risk,
            -result.metrics.expected_cost,
            result.algorithm_id,
        ),
    )


def _with_relative_scores(results: tuple[AlgorithmResult, ...], baseline_algorithm_id: str) -> tuple[AlgorithmResult, ...]:
    if not results:
        return ()
    baseline = next((result for result in results if result.algorithm_id == baseline_algorithm_id), results[0])
    baseline_metrics = baseline.metrics
    updated = []
    for result in results:
        relative = {
            "cost_delta_pct": _pct_delta(result.metrics.expected_cost, baseline_metrics.expected_cost),
            "eta_delta_pct": _pct_delta(result.metrics.avg_eta_s, baseline_metrics.avg_eta_s),
            "risk_delta_pct": _pct_delta(result.metrics.timeout_risk + result.metrics.no_accept_risk, baseline_metrics.timeout_risk + baseline_metrics.no_accept_risk),
            "score_delta_pct": 0.0,
        }
        score = _score(result.metrics, baseline_metrics)
        baseline_score = _score(baseline_metrics, baseline_metrics)
        relative["score_delta_pct"] = _pct_delta(score, baseline_score)
        metrics = replace(result.metrics, relative_to_baseline={key: round(value, 3) for key, value in relative.items()}, score=round(score, 3))
        updated.append(replace(result, metrics=metrics, risk_flags=_risk_flags(metrics)))
    return tuple(updated)


def _with_status(result: AlgorithmResult, status: str) -> AlgorithmResult:
    if result.status in {"failed", "timeout"}:
        return result
    return replace(result, status=status)


def _metrics_for(assignments: tuple[AssignmentDecision, ...], tick: SimulationTick, runtime_ms: float) -> AlgorithmMetrics:
    total_orders = len(_active_orders(tick))
    covered_orders = len({assignment.order_id for assignment in assignments})
    if total_orders == 0:
        return AlgorithmMetrics(1.0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, runtime_ms, {}, 100.0)

    eta_values = sorted(assignment.eta_s for assignment in assignments)
    avg_eta = sum(eta_values) / len(eta_values) if eta_values else 0.0
    p95_eta = _percentile(eta_values, 0.95)
    assigned_cost = sum(assignment.expected_cost for assignment in assignments)
    expected_cost = assigned_cost + (total_orders - covered_orders) * UNASSIGNED_ORDER_PENALTY
    unassigned_rate = (total_orders - covered_orders) / total_orders
    no_accept = _clamp(
        ((sum(1.0 - assignment.acceptance_probability for assignment in assignments) / len(assignments)) if assignments else 1.0) * 0.72
        + unassigned_rate * 0.28,
        0.0,
        1.0,
    )
    timeout = _clamp(
        ((sum(assignment.risk_score for assignment in assignments) / len(assignments)) if assignments else 1.0) * 0.74
        + unassigned_rate * 0.26,
        0.0,
        1.0,
    )
    return AlgorithmMetrics(
        coverage_rate=round(covered_orders / total_orders, 4),
        covered_orders=covered_orders,
        total_orders=total_orders,
        avg_eta_s=round(avg_eta, 3),
        p95_eta_s=round(p95_eta, 3),
        expected_cost=round(expected_cost, 3),
        courier_utilization=round(covered_orders / max(1, len(_available_couriers(tick))), 4),
        no_accept_risk=round(no_accept, 4),
        timeout_risk=round(timeout, 4),
        runtime_ms=runtime_ms,
        relative_to_baseline={},
        score=0.0,
    )


def _score(metrics: AlgorithmMetrics, baseline: AlgorithmMetrics) -> float:
    if metrics.total_orders == 0:
        return 100.0
    coverage_score = metrics.coverage_rate * 46.0
    cost_score = _ratio_score(baseline.expected_cost, metrics.expected_cost, 24.0)
    eta_score = _ratio_score(baseline.avg_eta_s, metrics.avg_eta_s, 14.0)
    risk_score = (1.0 - _clamp(metrics.no_accept_risk * 0.55 + metrics.timeout_risk * 0.45, 0.0, 1.0)) * 16.0
    return _clamp(coverage_score + cost_score + eta_score + risk_score, 0.0, 100.0)


def _ratio_score(baseline_value: float, value: float, weight: float) -> float:
    if baseline_value <= 0 and value <= 0:
        return weight
    if value <= 0:
        return weight
    return _clamp(baseline_value / value, 0.0, 1.35) / 1.35 * weight


def _assignment_profile(order: OrderState, courier: CourierState, tick: SimulationTick) -> _AssignmentProfile:
    merchant = _merchant_by_id(tick)[order.merchant_id]
    speed = _effective_speed_mps(courier, tick)
    pickup_eta = _distance_m(courier.position, merchant.position) / speed
    delivery_eta = _distance_m(merchant.position, order.destination) / speed
    elapsed_since_order = max(0.0, tick.sim_time_s - order.created_at_s)
    prep_wait = max(0.0, merchant.prep_time_s - elapsed_since_order * 0.55)
    eta = max(pickup_eta, prep_wait) + delivery_eta
    acceptance = _acceptance_probability(courier, order, tick)
    lateness_ratio = _clamp((tick.sim_time_s + eta - order.deadline_s) / 900.0, 0.0, 1.0)
    risk = _clamp((1.0 - acceptance) * 0.48 + lateness_ratio * 0.34 + merchant.pressure * 0.12 + _congestion(tick) * 0.06, 0.0, 1.0)
    expected_cost = eta * (1.0 + risk * 0.62) + (1.0 - acceptance) * 260.0 + lateness_ratio * 900.0
    return _AssignmentProfile(
        order=order,
        courier=courier,
        merchant=merchant,
        pickup_eta_s=round(pickup_eta, 3),
        delivery_eta_s=round(delivery_eta, 3),
        eta_s=round(eta, 3),
        expected_cost=round(expected_cost, 3),
        acceptance_probability=round(acceptance, 4),
        risk_score=round(risk, 4),
    )


def _assignment_decision(profile: _AssignmentProfile, rationale: str) -> AssignmentDecision:
    return AssignmentDecision(
        order_id=profile.order.id,
        courier_id=profile.courier.id,
        merchant_id=profile.merchant.id,
        pickup_eta_s=profile.pickup_eta_s,
        delivery_eta_s=profile.delivery_eta_s,
        eta_s=profile.eta_s,
        expected_cost=profile.expected_cost,
        acceptance_probability=profile.acceptance_probability,
        risk_score=profile.risk_score,
        rationale=rationale,
    )


def _scenario_features(session: SimulationSession, tick: SimulationTick) -> ScenarioFeatures:
    scenario = get_scenario(session.scenario_id)
    active_orders = _active_orders(tick)
    couriers = _available_couriers(tick)
    avg_willingness = sum(courier.willingness for courier in couriers) / len(couriers) if couriers else 0.0
    return ScenarioFeatures(
        scenario_id=session.scenario_id,
        scene_type=scenario.scene_type,
        weather=str(tick.map_state.get("weather", tick.traffic_state.get("weather", "clear"))),
        traffic_profile=str(tick.traffic_state.get("profile", "local-road-graph")),
        congestion_level=round(_congestion(tick), 4),
        order_pressure=round(len(active_orders) / max(1, len(couriers)), 4),
        courier_pressure=round(len(couriers) / max(1, len(active_orders)), 4) if active_orders else 1.0,
        active_order_count=len(active_orders),
        courier_count=len(couriers),
        avg_willingness=round(avg_willingness, 4),
        burst_active=any(order.burst_id for order in active_orders) or "order_burst" in tick.trigger_reasons,
    )


def _active_orders(tick: SimulationTick) -> tuple[OrderState, ...]:
    active_ids = set(tick.active_order_ids)
    if not active_ids:
        return tuple(order for order in tick.orders if order.status in {"new", "queued"})
    return tuple(order for order in tick.orders if order.id in active_ids and order.status in {"new", "queued"})


def _available_couriers(tick: SimulationTick) -> tuple[CourierState, ...]:
    return tuple(
        courier
        for courier in tick.couriers
        if courier.status != "offline" and len(courier.current_order_ids) < max(1, courier.capacity)
    )


def _merchant_by_id(tick: SimulationTick) -> dict[str, MerchantState]:
    return {merchant.id: merchant for merchant in tick.merchants}


def _effective_speed_mps(courier: CourierState, tick: SimulationTick) -> float:
    weather = str(tick.traffic_state.get("weather", tick.map_state.get("weather", "clear")))
    weather_factor = {"clear": 1.0, "rain": 0.82, "storm": 0.62, "event": 0.74}.get(weather, 1.0)
    traffic_factor = max(0.35, 1.0 - _congestion(tick) * 0.38)
    return max(0.8, courier.speed_mps * weather_factor * traffic_factor)


def _acceptance_probability(courier: CourierState, order: OrderState, tick: SimulationTick) -> float:
    weather = str(tick.traffic_state.get("weather", tick.map_state.get("weather", "clear")))
    weather_penalty = {"clear": 0.0, "rain": 0.08, "storm": 0.18, "event": 0.11}.get(weather, 0.0)
    return round(
        _clamp(
            courier.willingness
            + courier.acceptance_bias
            - courier.fatigue * 0.32
            - _congestion(tick) * 0.08
            - weather_penalty
            + order.priority * 0.12,
            0.02,
            0.99,
        ),
        4,
    )


def _best_acceptance_probability(order: OrderState, tick: SimulationTick) -> float:
    couriers = _available_couriers(tick)
    if not couriers:
        return 0.0
    return max(_acceptance_probability(courier, order, tick) for courier in couriers)


def _order_urgency(order: OrderState, tick: SimulationTick) -> float:
    time_left = max(1.0, order.deadline_s - tick.sim_time_s)
    deadline_pressure = _clamp(1.0 - time_left / 2_400.0, 0.0, 1.0)
    burst_bonus = 0.16 if order.burst_id else 0.0
    return _clamp(order.priority * 0.68 + deadline_pressure * 0.28 + burst_bonus, 0.0, 1.0)


def _unassigned_penalty(order: OrderState, tick: SimulationTick) -> float:
    return UNASSIGNED_ORDER_PENALTY * (0.72 + _order_urgency(order, tick) * 0.56)


def _route_overlays(assignments: tuple[AssignmentDecision, ...], tick: SimulationTick) -> tuple[dict[str, Any], ...]:
    couriers = {courier.id: courier for courier in tick.couriers}
    merchants = _merchant_by_id(tick)
    orders = {order.id: order for order in tick.orders}
    overlays = []
    for assignment in assignments:
        courier = couriers.get(assignment.courier_id)
        merchant = merchants.get(assignment.merchant_id)
        order = orders.get(assignment.order_id)
        if courier is None or merchant is None or order is None:
            continue
        overlays.append(
            {
                "assignment_id": f"{assignment.order_id}:{assignment.courier_id}",
                "order_id": assignment.order_id,
                "courier_id": assignment.courier_id,
                "points": [_position_to_dict(courier.position), _position_to_dict(merchant.position), _position_to_dict(order.destination)],
            }
        )
    return tuple(overlays)


def _reason_for(algorithm_id: str, metrics: AlgorithmMetrics, features: ScenarioFeatures) -> str:
    if metrics.total_orders == 0:
        return "No active orders; all algorithms stay idle."
    if algorithm_id == "nearest_greedy":
        return "Baseline dispatches the nearest available courier for each order."
    if algorithm_id == "cost_greedy":
        return "Greedy dispatch minimizes expected ETA and acceptance-adjusted cost."
    if algorithm_id == "risk_aware_greedy":
        return "Risk-aware greedy protects low-willingness and tight-deadline orders."
    if algorithm_id == "min_cost_matching":
        return "Matching evaluates the frozen batch globally instead of committing order by order."
    if algorithm_id == "sparse_cover":
        return "Sparse cover maximizes coverage under courier scarcity and merchant pressure."
    if algorithm_id == "flow_mcf":
        return "Flow-style dispatch balances cost, risk and priority across the batch."
    return f"{features.scene_type} scenario evaluated with local fallback logic."


def _risk_flags(metrics: AlgorithmMetrics) -> tuple[str, ...]:
    flags = []
    if metrics.coverage_rate < 1.0:
        flags.append("uncovered_orders")
    if metrics.no_accept_risk >= 0.45:
        flags.append("high_no_accept_risk")
    if metrics.timeout_risk >= 0.42:
        flags.append("high_timeout_risk")
    if metrics.courier_utilization >= 0.92 and metrics.total_orders > 0:
        flags.append("courier_pool_saturated")
    return tuple(flags)


def _decision_points(compare_run: CompareRun, results: tuple[AlgorithmResult, ...], selected: AlgorithmResult) -> tuple[DecisionPoint, ...]:
    baseline = next((result for result in results if result.algorithm_id == compare_run.baseline_algorithm_id), None)
    points = [
        DecisionPoint(
            id=_stable_id(compare_run.compare_run_id, "selected", selected.algorithm_id),
            time_s=0.0,
            algorithm_id=selected.algorithm_id,
            title="Selected dispatch policy",
            summary=selected.reason,
            evidence={
                "score": selected.metrics.score,
                "coverage_rate": selected.metrics.coverage_rate,
                "expected_cost": selected.metrics.expected_cost,
                "timeout_risk": selected.metrics.timeout_risk,
            },
            impact="selected",
            map_focus=tuple(assignment.order_id for assignment in selected.assignments[:5]),
        )
    ]
    if baseline is not None and baseline.algorithm_id != selected.algorithm_id:
        points.append(
            DecisionPoint(
                id=_stable_id(compare_run.compare_run_id, "baseline-delta"),
                time_s=0.0,
                algorithm_id=selected.algorithm_id,
                title="Compared with nearest greedy",
                summary=(
                    f"Cost delta {selected.metrics.relative_to_baseline.get('cost_delta_pct', 0.0):.1f}%, "
                    f"risk delta {selected.metrics.relative_to_baseline.get('risk_delta_pct', 0.0):.1f}%."
                ),
                evidence=selected.metrics.relative_to_baseline,
                impact="replanned",
                map_focus=tuple(assignment.courier_id for assignment in selected.assignments[:5]),
            )
        )
    weakest = min(results, key=lambda result: (result.metrics.score, result.metrics.coverage_rate, -result.metrics.expected_cost))
    if weakest.algorithm_id != selected.algorithm_id:
        points.append(
            DecisionPoint(
                id=_stable_id(compare_run.compare_run_id, "rejected", weakest.algorithm_id),
                time_s=0.0,
                algorithm_id=weakest.algorithm_id,
                title="Rejected weaker policy",
                summary=f"{weakest.label} is weaker on this tick: {', '.join(weakest.risk_flags) or 'lower score'}.",
                evidence={
                    "score": weakest.metrics.score,
                    "coverage_rate": weakest.metrics.coverage_rate,
                    "expected_cost": weakest.metrics.expected_cost,
                    "risk_flags": list(weakest.risk_flags),
                },
                impact="rejected",
                map_focus=tuple(assignment.order_id for assignment in weakest.assignments[:5]),
            )
        )
    return tuple(points)


def _timeline_delta(
    compare_run: CompareRun,
    results: tuple[AlgorithmResult, ...],
    selected: AlgorithmResult,
    tick: SimulationTick,
) -> tuple[TimelineEvent, ...]:
    events = [
        TimelineEvent(
            event_id=_stable_id(compare_run.compare_run_id, "started"),
            session_id=compare_run.session_id,
            tick_id=compare_run.tick_id,
            sim_time_s=tick.sim_time_s,
            event_type="compare_started",
            title="Compare started",
            summary=f"{len(results)} algorithms evaluated on one frozen tick.",
            entity_ids=tick.active_order_ids,
            severity="notice",
        )
    ]
    for result in results:
        events.append(
            TimelineEvent(
                event_id=_stable_id(compare_run.compare_run_id, "algorithm", result.algorithm_id),
                session_id=compare_run.session_id,
                tick_id=compare_run.tick_id,
                sim_time_s=tick.sim_time_s,
                event_type="algorithm_completed",
                title=f"{result.label} completed",
                summary=f"Coverage {result.metrics.coverage_rate:.0%}, score {result.metrics.score:.1f}.",
                entity_ids=tuple(assignment.order_id for assignment in result.assignments[:5]),
                severity="info",
            )
        )
    events.append(
        TimelineEvent(
            event_id=_stable_id(compare_run.compare_run_id, "selected", selected.algorithm_id),
            session_id=compare_run.session_id,
            tick_id=compare_run.tick_id,
            sim_time_s=tick.sim_time_s,
            event_type="decision_selected",
            title="Decision selected",
            summary=f"{selected.label} selected for the current dispatch tick.",
            entity_ids=tuple(assignment.order_id for assignment in selected.assignments[:5]),
            severity="notice",
        )
    )
    return tuple(events)


def _failed_result(algorithm_id: str, tick: SimulationTick, reason: str) -> AlgorithmResult:
    family, label = ALGORITHM_META.get(algorithm_id, ("unknown", algorithm_id))
    metrics = AlgorithmMetrics(
        coverage_rate=0.0 if _active_orders(tick) else 1.0,
        covered_orders=0,
        total_orders=len(_active_orders(tick)),
        avg_eta_s=0.0,
        p95_eta_s=0.0,
        expected_cost=len(_active_orders(tick)) * UNASSIGNED_ORDER_PENALTY,
        courier_utilization=0.0,
        no_accept_risk=1.0 if _active_orders(tick) else 0.0,
        timeout_risk=1.0 if _active_orders(tick) else 0.0,
        runtime_ms=0.0,
        relative_to_baseline={},
        score=0.0,
    )
    return AlgorithmResult(algorithm_id, family, label, "failed", metrics, (), (), reason, _risk_flags(metrics))


def _estimated_runtime_ms(algorithm_id: str, order_count: int, courier_count: int) -> float:
    base = {
        "nearest_greedy": 3.0,
        "cost_greedy": 4.2,
        "risk_aware_greedy": 5.4,
        "min_cost_matching": 15.0,
        "sparse_cover": 10.5,
        "flow_mcf": 18.0,
        "autosolver_agent": 22.0,
    }.get(algorithm_id, 2.0)
    scale = order_count * max(1, courier_count) * {
        "nearest_greedy": 0.04,
        "cost_greedy": 0.05,
        "risk_aware_greedy": 0.06,
        "min_cost_matching": 0.14,
        "sparse_cover": 0.08,
        "flow_mcf": 0.16,
        "autosolver_agent": 0.03,
    }.get(algorithm_id, 0.04)
    return round(base + scale, 3)


def _pct_delta(value: float, baseline_value: float) -> float:
    if abs(baseline_value) < 1e-9:
        return 0.0 if abs(value) < 1e-9 else 100.0
    return (value - baseline_value) / abs(baseline_value) * 100.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    index = min(len(values) - 1, max(0, math.ceil(len(values) * percentile) - 1))
    return values[index]


def _position_to_dict(position: Position) -> dict[str, float | None]:
    return {"lat": position.lat, "lng": position.lng, "screen_x": position.screen_x, "screen_y": position.screen_y}


def _distance_m(left: Position, right: Position) -> float:
    avg_lat = math.radians((left.lat + right.lat) / 2.0)
    d_lat = (right.lat - left.lat) * EARTH_METERS_PER_DEGREE
    d_lng = (right.lng - left.lng) * EARTH_METERS_PER_DEGREE * math.cos(avg_lat)
    return math.hypot(d_lat, d_lng)


def _congestion(tick: SimulationTick) -> float:
    return _clamp(float(tick.traffic_state.get("congestion_level", 0.5)), 0.0, 1.0)


def _stable_id(*parts: object) -> str:
    return hashlib.sha1("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
