from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any

from web_agent_demo.simulation_engine import Position, simulation_to_dict


DAY_SIMULATION_CONTRACT_VERSION = "day-simulation-contract-v1"
DAY_START_S = 7 * 60 * 60
DAY_END_S = 23 * 60 * 60
DEFAULT_TIME_SLICE_S = 15 * 60

DAY_SIMULATION_ENDPOINTS = {
    "scenarios": "/api/day-simulation/scenarios",
    "run": "/api/day-simulation/run",
    "frame": "/api/day-simulation/frame",
    "memory": "/api/day-simulation/memory",
}


@dataclass(frozen=True)
class DaySimulationControls:
    courier_count: int = 48
    order_scale: float = 1.0
    weather: str = "mixed"
    congestion_profile: str = "weekday"
    time_slice_s: int = DEFAULT_TIME_SLICE_S
    baseline_algorithm_id: str = "nearest_greedy"
    challenger_algorithm_id: str = "autosolver_agent"
    memory_mode: str = "read-write"
    predictor_mode: str = "auto"


@dataclass(frozen=True)
class DayScenario:
    id: str
    name: str
    description: str
    city_label: str
    map_provider: str
    map_center: Position
    map_bounds: tuple[Position, Position]
    day_start_s: int
    day_end_s: int
    time_slice_s: int
    demand_phases: tuple[str, ...]
    shock_profiles: tuple[str, ...]
    merchant_zones: tuple[str, ...]
    algorithms: tuple[str, ...]
    default_controls: DaySimulationControls
    visual_directive: str


@dataclass(frozen=True)
class DayMerchant:
    id: str
    label: str
    zone_id: str
    category: str
    position: Position
    peak_capacity: int
    prep_time_s: float


@dataclass(frozen=True)
class DayCourier:
    id: str
    label: str
    home_zone_id: str
    shift_start_s: int
    shift_end_s: int
    capacity: int
    base_speed_mps: float
    willingness: float
    start_position: Position


@dataclass(frozen=True)
class DayOrder:
    id: str
    merchant_id: str
    created_at_s: int
    deadline_s: int
    demand_phase: str
    merchant_position: Position
    destination: Position
    prep_time_s: float
    priority: float
    basket_value_yuan: float
    penalty_yuan: float
    risk_tags: tuple[str, ...]


@dataclass(frozen=True)
class DayShock:
    id: str
    shock_type: str
    start_s: int
    end_s: int
    affected_zone_ids: tuple[str, ...]
    severity: float
    summary: str


@dataclass(frozen=True)
class TimeSlice:
    id: str
    index: int
    start_s: int
    end_s: int
    label: str
    demand_phase: str
    weather: str
    congestion_level: float
    courier_supply: int
    order_ids: tuple[str, ...]
    shock_ids: tuple[str, ...]
    compare_due: bool


@dataclass(frozen=True)
class DispatchAssignment:
    order_id: str
    courier_id: str
    merchant_id: str
    pickup_eta_s: float
    delivery_eta_s: float
    total_eta_s: float
    expected_cost_yuan: float
    timeout_risk: float
    rationale: str


@dataclass(frozen=True)
class DayMetrics:
    total_orders: int
    delivered_orders: int
    assigned_orders: int
    late_orders: int
    coverage_rate: float
    avg_eta_s: float
    p95_eta_s: float
    total_time_cost_s: float
    total_distance_m: float
    total_cost_yuan: float
    timeout_risk: float
    courier_utilization: float
    gross_revenue_yuan: float


@dataclass(frozen=True)
class MetricDelta:
    time_saved_s: float
    cost_saved_yuan: float
    extra_delivered_orders: int
    timeout_risk_delta: float
    utilization_delta: float
    headline: str


@dataclass(frozen=True)
class AlgorithmFrame:
    algorithm_id: str
    label: str
    status: str
    courier_positions: tuple[dict[str, Any], ...]
    active_order_ids: tuple[str, ...]
    completed_order_ids: tuple[str, ...]
    assignments: tuple[DispatchAssignment, ...]
    route_overlays: tuple[dict[str, Any], ...]
    metrics: DayMetrics
    decision_summary: str


@dataclass(frozen=True)
class SideBySideFrame:
    id: str
    scenario_id: str
    time_slice_id: str
    sim_time_s: int
    baseline: AlgorithmFrame
    challenger: AlgorithmFrame
    delta: MetricDelta
    highlighted_order_ids: tuple[str, ...]
    highlighted_courier_ids: tuple[str, ...]
    reasoning_trace_ids: tuple[str, ...]
    memory_event_ids: tuple[str, ...]


@dataclass(frozen=True)
class AlgorithmCandidateScore:
    algorithm_id: str
    score: float
    estimated_runtime_ms: float
    expected_time_cost_s: float
    expected_cost_yuan: float
    risk_score: float
    reason: str


@dataclass(frozen=True)
class ReasoningTrace:
    id: str
    frame_id: str
    algorithm_id: str
    selected_strategy: str
    candidate_scores: tuple[AlgorithmCandidateScore, ...]
    evidence: dict[str, Any]
    rationale: str
    expected_impact: MetricDelta
    time_budget_ms: int
    memory_event_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvolutionMemoryEvent:
    id: str
    frame_id: str
    event_type: str
    context_signature: str
    recalled_case_ids: tuple[str, ...]
    chosen_algorithm_id: str
    learned_rule: str
    confidence_before: float
    confidence_after: float
    writeback: bool
    secret_handling: str = "env-only-redacted"


@dataclass(frozen=True)
class AlgorithmDayRun:
    run_id: str
    scenario_id: str
    algorithm_id: str
    label: str
    family: str
    status: str
    metrics: DayMetrics
    frame_ids: tuple[str, ...]
    decision_trace_ids: tuple[str, ...]
    memory_event_ids: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class DaySimulationContract:
    contract_version: str
    scenario: DayScenario
    merchants: tuple[DayMerchant, ...]
    couriers: tuple[DayCourier, ...]
    orders: tuple[DayOrder, ...]
    shocks: tuple[DayShock, ...]
    time_slices: tuple[TimeSlice, ...]
    baseline_run: AlgorithmDayRun
    challenger_run: AlgorithmDayRun
    frames: tuple[SideBySideFrame, ...]
    reasoning_traces: tuple[ReasoningTrace, ...]
    evolution_events: tuple[EvolutionMemoryEvent, ...]
    api_endpoints: dict[str, str]
    privacy: dict[str, str]


@dataclass(frozen=True)
class DaySimulationWorld:
    scenario: DayScenario
    seed: str
    controls: DaySimulationControls
    merchants: tuple[DayMerchant, ...]
    couriers: tuple[DayCourier, ...]
    orders: tuple[DayOrder, ...]
    shocks: tuple[DayShock, ...]
    time_slices: tuple[TimeSlice, ...]
    summary: dict[str, Any]


def day_scenario_catalog() -> tuple[DayScenario, ...]:
    return (
        DayScenario(
            id="weekday_full_day",
            name="Weekday full-day delivery replay",
            description="A full-day order stream spanning breakfast, lunch peak, afternoon tea, dinner peak and night supply gaps.",
            city_label="Shanghai core commerce simulation",
            map_provider="local-road-graph",
            map_center=Position(31.2304, 121.4737, 50.0, 50.0),
            map_bounds=(Position(31.2148, 121.4520, 6.0, 92.0), Position(31.2460, 121.4954, 94.0, 8.0)),
            day_start_s=DAY_START_S,
            day_end_s=DAY_END_S,
            time_slice_s=DEFAULT_TIME_SLICE_S,
            demand_phases=("breakfast", "lunch_peak", "afternoon_tea", "dinner_peak", "night_supply_gap"),
            shock_profiles=("rain_slowdown", "merchant_burst", "courier_shortage", "road_congestion"),
            merchant_zones=("office_core", "mall_foodcourt", "metro_exit", "residential_edge"),
            algorithms=("nearest_greedy", "cost_greedy", "risk_aware_greedy", "min_cost_matching", "flow_mcf", "autosolver_agent"),
            default_controls=DaySimulationControls(),
            visual_directive="Side-by-side operational replay on the existing project map; no complex wireframe-first reasoning graph.",
        ),
    )


def generate_full_day_world(
    scenario_id: str = "weekday_full_day",
    seed: str = "demo",
    controls: DaySimulationControls | None = None,
) -> DaySimulationWorld:
    scenario = get_day_scenario(scenario_id)
    normalized = _normalize_day_controls(controls or scenario.default_controls)
    merchants = _generate_day_merchants(scenario, seed)
    couriers = _generate_day_couriers(scenario, seed, normalized)
    shocks = _generate_day_shocks(scenario, seed, normalized)
    orders_by_slice: dict[int, list[DayOrder]] = {}
    slices: list[TimeSlice] = []

    for index, start_s in enumerate(range(scenario.day_start_s, scenario.day_end_s, normalized.time_slice_s)):
        end_s = min(start_s + normalized.time_slice_s, scenario.day_end_s)
        phase = _phase_for_second(start_s)
        active_shocks = _active_shocks(shocks, start_s, end_s)
        weather = _weather_for_slice(normalized, active_shocks, start_s)
        congestion = _congestion_for_slice(normalized, phase, active_shocks, start_s)
        supply = _courier_supply(couriers, active_shocks, start_s)
        orders = _generate_orders_for_slice(
            scenario=scenario,
            seed=seed,
            controls=normalized,
            merchants=merchants,
            phase=phase,
            start_s=start_s,
            end_s=end_s,
            index=index,
            weather=weather,
            congestion_level=congestion,
            active_shocks=active_shocks,
        )
        orders_by_slice[index] = list(orders)
        slices.append(
            TimeSlice(
                id=_time_slice_id(start_s),
                index=index,
                start_s=start_s,
                end_s=end_s,
                label=_time_label(start_s, phase),
                demand_phase=phase,
                weather=weather,
                congestion_level=congestion,
                courier_supply=supply,
                order_ids=tuple(order.id for order in orders),
                shock_ids=tuple(shock.id for shock in active_shocks),
                compare_due=bool(active_shocks) or len(orders) >= max(4, int(normalized.courier_count * 0.16)),
            )
        )

    all_orders = tuple(order for index in sorted(orders_by_slice) for order in orders_by_slice[index])
    time_slices = tuple(slices)
    return DaySimulationWorld(
        scenario=scenario,
        seed=str(seed),
        controls=normalized,
        merchants=merchants,
        couriers=couriers,
        orders=all_orders,
        shocks=shocks,
        time_slices=time_slices,
        summary=_world_summary(all_orders, shocks, time_slices, couriers),
    )


def build_contract_preview(scenario_id: str = "weekday_full_day") -> DaySimulationContract:
    scenario = get_day_scenario(scenario_id)
    merchant = DayMerchant(
        id="M001",
        label="Merchant 1",
        zone_id="office_core",
        category="quick_service",
        position=Position(31.2312, 121.4734, 48.0, 45.0),
        peak_capacity=42,
        prep_time_s=360.0,
    )
    courier = DayCourier(
        id="R001",
        label="Courier 1",
        home_zone_id="office_core",
        shift_start_s=DAY_START_S,
        shift_end_s=DAY_END_S,
        capacity=3,
        base_speed_mps=4.6,
        willingness=0.82,
        start_position=Position(31.2298, 121.4722, 44.0, 52.0),
    )
    order = DayOrder(
        id="O-1200-0001",
        merchant_id=merchant.id,
        created_at_s=12 * 60 * 60,
        deadline_s=12 * 60 * 60 + 35 * 60,
        demand_phase="lunch_peak",
        merchant_position=merchant.position,
        destination=Position(31.2364, 121.4811, 64.0, 34.0),
        prep_time_s=merchant.prep_time_s,
        priority=0.86,
        basket_value_yuan=45.0,
        penalty_yuan=9.5,
        risk_tags=("lunch_peak", "tight_deadline"),
    )
    shock = DayShock(
        id="S-rain-1200",
        shock_type="rain_slowdown",
        start_s=11 * 60 * 60 + 45 * 60,
        end_s=13 * 60 * 60,
        affected_zone_ids=("office_core", "mall_foodcourt"),
        severity=0.62,
        summary="Lunch-peak rain slows arterial roads.",
    )
    time_slice = TimeSlice(
        id="TS-1200",
        index=20,
        start_s=12 * 60 * 60,
        end_s=12 * 60 * 60 + DEFAULT_TIME_SLICE_S,
        label="12:00 lunch peak",
        demand_phase="lunch_peak",
        weather="rain",
        congestion_level=0.74,
        courier_supply=48,
        order_ids=(order.id,),
        shock_ids=(shock.id,),
        compare_due=True,
    )
    greedy_metrics = DayMetrics(
        total_orders=1,
        delivered_orders=0,
        assigned_orders=1,
        late_orders=0,
        coverage_rate=1.0,
        avg_eta_s=1680.0,
        p95_eta_s=1680.0,
        total_time_cost_s=1680.0,
        total_distance_m=3850.0,
        total_cost_yuan=18.8,
        timeout_risk=0.31,
        courier_utilization=0.58,
        gross_revenue_yuan=45.0,
    )
    autosolver_metrics = DayMetrics(
        total_orders=1,
        delivered_orders=0,
        assigned_orders=1,
        late_orders=0,
        coverage_rate=1.0,
        avg_eta_s=1320.0,
        p95_eta_s=1320.0,
        total_time_cost_s=1320.0,
        total_distance_m=3180.0,
        total_cost_yuan=15.2,
        timeout_risk=0.18,
        courier_utilization=0.64,
        gross_revenue_yuan=45.0,
    )
    delta = MetricDelta(
        time_saved_s=360.0,
        cost_saved_yuan=3.6,
        extra_delivered_orders=0,
        timeout_risk_delta=-0.13,
        utilization_delta=0.06,
        headline="AutoSolver saves 6.0 minutes and 3.6 yuan in rainy lunch peak.",
    )
    greedy_assignment = DispatchAssignment(
        order_id=order.id,
        courier_id=courier.id,
        merchant_id=merchant.id,
        pickup_eta_s=620.0,
        delivery_eta_s=1060.0,
        total_eta_s=1680.0,
        expected_cost_yuan=18.8,
        timeout_risk=0.31,
        rationale="nearest_greedy selects the nearest idle courier but ignores rainy arterial congestion.",
    )
    autosolver_assignment = DispatchAssignment(
        order_id=order.id,
        courier_id=courier.id,
        merchant_id=merchant.id,
        pickup_eta_s=520.0,
        delivery_eta_s=800.0,
        total_eta_s=1320.0,
        expected_cost_yuan=15.2,
        timeout_risk=0.18,
        rationale="autosolver_agent combines rainy-day memory and risk scoring to avoid congested routes.",
    )
    baseline_frame = AlgorithmFrame(
        algorithm_id="nearest_greedy",
        label="Pure Greedy",
        status="evaluated",
        courier_positions=(_courier_snapshot(courier),),
        active_order_ids=(order.id,),
        completed_order_ids=(),
        assignments=(greedy_assignment,),
        route_overlays=(_route_overlay(order, courier, "baseline"),),
        metrics=greedy_metrics,
        decision_summary="Dispatches by nearest distance while ignoring rain congestion and future order pressure.",
    )
    challenger_frame = AlgorithmFrame(
        algorithm_id="autosolver_agent",
        label="AutoSolver Agent",
        status="selected",
        courier_positions=(_courier_snapshot(courier),),
        active_order_ids=(order.id,),
        completed_order_ids=(),
        assignments=(autosolver_assignment,),
        route_overlays=(_route_overlay(order, courier, "challenger"),),
        metrics=autosolver_metrics,
        decision_summary="Uses memory recall and risk scoring to choose a lower-timeout route.",
    )
    frame = SideBySideFrame(
        id="F-TS-1200",
        scenario_id=scenario.id,
        time_slice_id=time_slice.id,
        sim_time_s=time_slice.start_s,
        baseline=baseline_frame,
        challenger=challenger_frame,
        delta=delta,
        highlighted_order_ids=(order.id,),
        highlighted_courier_ids=(courier.id,),
        reasoning_trace_ids=("RT-F-TS-1200",),
        memory_event_ids=("ME-F-TS-1200",),
    )
    memory_event = EvolutionMemoryEvent(
        id="ME-F-TS-1200",
        frame_id=frame.id,
        event_type="memory_writeback",
        context_signature="lunch_peak|rain|high_congestion|tight_deadline",
        recalled_case_ids=("rain-lunch-previous-01",),
        chosen_algorithm_id="autosolver_agent",
        learned_rule="For rainy lunch peak with tight deadlines, prefer risk-aware composition over nearest greedy.",
        confidence_before=0.61,
        confidence_after=0.72,
        writeback=True,
    )
    reasoning = ReasoningTrace(
        id="RT-F-TS-1200",
        frame_id=frame.id,
        algorithm_id="autosolver_agent",
        selected_strategy="risk-aware memory-guided dispatch",
        candidate_scores=(
            AlgorithmCandidateScore(
                algorithm_id="nearest_greedy",
                score=0.52,
                estimated_runtime_ms=12.0,
                expected_time_cost_s=1680.0,
                expected_cost_yuan=18.8,
                risk_score=0.31,
                reason="Nearest distance gives a quick feasible answer but carries high rain congestion risk.",
            ),
            AlgorithmCandidateScore(
                algorithm_id="autosolver_agent",
                score=0.78,
                estimated_runtime_ms=420.0,
                expected_time_cost_s=1320.0,
                expected_cost_yuan=15.2,
                risk_score=0.18,
                reason="Memory recall matches rainy lunch peak and reduces timeout risk.",
            ),
        ),
        evidence={"weather": "rain", "congestion_level": 0.74, "memory_hits": 1, "time_budget_ms": 10_000},
        rationale="On the same order stream, AutoSolver trades small solver time for lower route risk and fulfillment cost.",
        expected_impact=delta,
        time_budget_ms=10_000,
        memory_event_ids=(memory_event.id,),
    )
    baseline_run = AlgorithmDayRun(
        run_id="DAY-RUN-nearest_greedy-preview",
        scenario_id=scenario.id,
        algorithm_id="nearest_greedy",
        label="Pure Greedy",
        family="baseline",
        status="contract-preview",
        metrics=greedy_metrics,
        frame_ids=(frame.id,),
        decision_trace_ids=(),
        memory_event_ids=(),
        summary="Baseline dispatches by nearest distance to expose full-day cumulative time and cost gaps.",
    )
    challenger_run = AlgorithmDayRun(
        run_id="DAY-RUN-autosolver_agent-preview",
        scenario_id=scenario.id,
        algorithm_id="autosolver_agent",
        label="AutoSolver Agent",
        family="agent",
        status="contract-preview",
        metrics=autosolver_metrics,
        frame_ids=(frame.id,),
        decision_trace_ids=(reasoning.id,),
        memory_event_ids=(memory_event.id,),
        summary="The agent chooses strategies from scene features, historical memory and candidate algorithm scores.",
    )
    return DaySimulationContract(
        contract_version=DAY_SIMULATION_CONTRACT_VERSION,
        scenario=scenario,
        merchants=(merchant,),
        couriers=(courier,),
        orders=(order,),
        shocks=(shock,),
        time_slices=(time_slice,),
        baseline_run=baseline_run,
        challenger_run=challenger_run,
        frames=(frame,),
        reasoning_traces=(reasoning,),
        evolution_events=(memory_event,),
        api_endpoints=dict(DAY_SIMULATION_ENDPOINTS),
        privacy={
            "llm_api_key": "env-only",
            "llm_base_url": "env-only",
            "llm_model": "env-only",
            "secret_handling": "env-only-redacted",
        },
    )


def get_day_scenario(scenario_id: str) -> DayScenario:
    for scenario in day_scenario_catalog():
        if scenario.id == scenario_id:
            return scenario
    raise KeyError(f"unknown day simulation scenario: {scenario_id}")


def day_contract_to_dict(value: Any) -> Any:
    return simulation_to_dict(value)


def day_world_to_dict(value: Any) -> Any:
    return simulation_to_dict(value)


def _courier_snapshot(courier: DayCourier) -> dict[str, Any]:
    return {
        "courier_id": courier.id,
        "label": courier.label,
        "position": simulation_to_dict(courier.start_position),
        "status": "available",
        "capacity": courier.capacity,
    }


def _route_overlay(order: DayOrder, courier: DayCourier, lane: str) -> dict[str, Any]:
    return {
        "lane": lane,
        "order_id": order.id,
        "courier_id": courier.id,
        "polyline": [
            simulation_to_dict(courier.start_position),
            simulation_to_dict(order.merchant_position),
            simulation_to_dict(order.destination),
        ],
    }


def _normalize_day_controls(controls: DaySimulationControls) -> DaySimulationControls:
    weather = controls.weather if controls.weather in {"mixed", "clear", "rain", "storm", "event"} else "mixed"
    profile = controls.congestion_profile if controls.congestion_profile in {"weekday", "smooth", "rainy", "event"} else "weekday"
    return DaySimulationControls(
        courier_count=max(1, min(500, int(controls.courier_count))),
        order_scale=round(_clamp(float(controls.order_scale), 0.1, 3.0), 4),
        weather=weather,
        congestion_profile=profile,
        time_slice_s=max(5 * 60, min(60 * 60, int(controls.time_slice_s))),
        baseline_algorithm_id=controls.baseline_algorithm_id or "nearest_greedy",
        challenger_algorithm_id=controls.challenger_algorithm_id or "autosolver_agent",
        memory_mode=controls.memory_mode if controls.memory_mode in {"off", "read-only", "read-write"} else "read-write",
        predictor_mode=controls.predictor_mode if controls.predictor_mode in {"fallback", "auto", "external"} else "auto",
    )


def _generate_day_merchants(scenario: DayScenario, seed: str) -> tuple[DayMerchant, ...]:
    categories = ("quick_service", "tea", "snack", "noodle", "rice_bowl", "bakery")
    merchants: list[DayMerchant] = []
    for index in range(18):
        zone_id = scenario.merchant_zones[index % len(scenario.merchant_zones)]
        rng = _rng(seed, scenario.id, "merchant", index)
        merchants.append(
            DayMerchant(
                id=f"M{index + 1:03d}",
                label=f"Merchant {index + 1}",
                zone_id=zone_id,
                category=categories[index % len(categories)],
                position=_zone_position(scenario, zone_id, rng, spread=0.105),
                peak_capacity=28 + int(rng.random() * 36),
                prep_time_s=round(220 + rng.random() * 260 + (index % 3) * 35, 1),
            )
        )
    return tuple(merchants)


def _generate_day_couriers(
    scenario: DayScenario,
    seed: str,
    controls: DaySimulationControls,
) -> tuple[DayCourier, ...]:
    couriers: list[DayCourier] = []
    for index in range(controls.courier_count):
        rng = _rng(seed, scenario.id, "courier", index)
        shift_template = index % 6
        if shift_template in {0, 1}:
            shift_start, shift_end = DAY_START_S, 16 * 60 * 60
        elif shift_template in {2, 3}:
            shift_start, shift_end = 10 * 60 * 60, 21 * 60 * 60
        elif shift_template == 4:
            shift_start, shift_end = 16 * 60 * 60, DAY_END_S
        else:
            shift_start, shift_end = DAY_START_S, DAY_END_S
        zone_id = scenario.merchant_zones[(index + int(rng.random() * 10)) % len(scenario.merchant_zones)]
        couriers.append(
            DayCourier(
                id=f"R{index + 1:03d}",
                label=f"Courier {index + 1}",
                home_zone_id=zone_id,
                shift_start_s=shift_start,
                shift_end_s=shift_end,
                capacity=3 if index % 5 == 0 else 2,
                base_speed_mps=round(3.8 + rng.random() * 1.35, 3),
                willingness=round(_clamp(0.52 + rng.random() * 0.38, 0.05, 0.98), 4),
                start_position=_zone_position(scenario, zone_id, rng, spread=0.14),
            )
        )
    return tuple(couriers)


def _generate_day_shocks(
    scenario: DayScenario,
    seed: str,
    controls: DaySimulationControls,
) -> tuple[DayShock, ...]:
    rng = _rng(seed, scenario.id, "shocks", controls.weather, controls.congestion_profile)
    rain_severity = 0.52 + rng.random() * 0.24
    if controls.weather == "clear":
        rain_severity = 0.22
    elif controls.weather == "storm":
        rain_severity = 0.86
    road_severity = 0.45 + rng.random() * 0.28
    if controls.congestion_profile == "smooth":
        road_severity = 0.24
    elif controls.congestion_profile == "event":
        road_severity = 0.82
    shortage_severity = 0.36 + rng.random() * 0.24
    burst_severity = 0.55 + rng.random() * 0.24
    return (
        DayShock(
            id="S-rain-lunch",
            shock_type="rain_slowdown",
            start_s=11 * 60 * 60 + 45 * 60,
            end_s=13 * 60 * 60 + 15 * 60,
            affected_zone_ids=("office_core", "mall_foodcourt"),
            severity=round(rain_severity, 4),
            summary="Rain slows lunch-peak arterial links.",
        ),
        DayShock(
            id="S-merchant-burst-lunch",
            shock_type="merchant_burst",
            start_s=12 * 60 * 60,
            end_s=12 * 60 * 60 + 45 * 60,
            affected_zone_ids=("mall_foodcourt", "metro_exit"),
            severity=round(burst_severity, 4),
            summary="Merchant burst creates simultaneous lunch orders.",
        ),
        DayShock(
            id="S-road-dinner",
            shock_type="road_congestion",
            start_s=17 * 60 * 60 + 30 * 60,
            end_s=19 * 60 * 60 + 15 * 60,
            affected_zone_ids=("office_core", "residential_edge"),
            severity=round(road_severity, 4),
            summary="Dinner commute congestion slows cross-zone movement.",
        ),
        DayShock(
            id="S-courier-night",
            shock_type="courier_shortage",
            start_s=21 * 60 * 60,
            end_s=22 * 60 * 60 + 30 * 60,
            affected_zone_ids=tuple(scenario.merchant_zones),
            severity=round(shortage_severity, 4),
            summary="Night supply gap reduces available courier pool.",
        ),
    )


def _generate_orders_for_slice(
    scenario: DayScenario,
    seed: str,
    controls: DaySimulationControls,
    merchants: tuple[DayMerchant, ...],
    phase: str,
    start_s: int,
    end_s: int,
    index: int,
    weather: str,
    congestion_level: float,
    active_shocks: tuple[DayShock, ...],
) -> tuple[DayOrder, ...]:
    rng = _rng(seed, scenario.id, "orders", start_s, phase)
    count = _order_count_for_slice(controls, phase, start_s, end_s, active_shocks, rng)
    affected_zones = {
        zone_id
        for shock in active_shocks
        if shock.shock_type == "merchant_burst"
        for zone_id in shock.affected_zone_ids
    }
    orders: list[DayOrder] = []
    for offset in range(count):
        merchant = _merchant_for_order(merchants, rng, phase, affected_zones, offset)
        created_at = start_s + int((offset + 1) * max(1, (end_s - start_s)) / (count + 1))
        order_rng = _rng(seed, scenario.id, "order-detail", start_s, offset, merchant.id)
        priority = _priority_for_order(phase, weather, congestion_level, order_rng)
        deadline_window = _deadline_window_s(phase, weather, congestion_level, priority, order_rng)
        destination = _destination_for_order(scenario, merchant.position, order_rng, phase)
        risk_tags = _risk_tags(phase, weather, congestion_level, active_shocks, priority)
        orders.append(
            DayOrder(
                id=f"O-{created_at // 60:04d}-{index:03d}-{offset + 1:03d}",
                merchant_id=merchant.id,
                created_at_s=created_at,
                deadline_s=created_at + deadline_window,
                demand_phase=phase,
                merchant_position=merchant.position,
                destination=destination,
                prep_time_s=round(merchant.prep_time_s * _prep_multiplier(active_shocks, congestion_level), 1),
                priority=priority,
                basket_value_yuan=round(18.0 + order_rng.random() * 64.0 + priority * 12.0, 2),
                penalty_yuan=round(4.0 + priority * 9.5 + len(risk_tags) * 0.85, 2),
                risk_tags=risk_tags,
            )
        )
    return tuple(orders)


def _order_count_for_slice(
    controls: DaySimulationControls,
    phase: str,
    start_s: int,
    end_s: int,
    active_shocks: tuple[DayShock, ...],
    rng: random.Random,
) -> int:
    base_by_phase = {
        "breakfast": 4.2,
        "lunch_peak": 11.5,
        "afternoon_tea": 5.0,
        "dinner_peak": 10.2,
        "night_supply_gap": 3.3,
    }
    count = base_by_phase.get(phase, 4.0) * controls.order_scale * ((end_s - start_s) / DEFAULT_TIME_SLICE_S)
    for shock in active_shocks:
        if shock.shock_type == "merchant_burst":
            count *= 1.0 + shock.severity * 0.95
        elif shock.shock_type in {"rain_slowdown", "road_congestion"}:
            count *= 1.0 + shock.severity * 0.12
    jitter = 0.72 + rng.random() * 0.62
    return max(1, int(round(count * jitter)))


def _merchant_for_order(
    merchants: tuple[DayMerchant, ...],
    rng: random.Random,
    phase: str,
    affected_zones: set[str],
    offset: int,
) -> DayMerchant:
    if affected_zones:
        candidates = tuple(merchant for merchant in merchants if merchant.zone_id in affected_zones)
    else:
        candidates = merchants
    phase_bias = {"breakfast": 0, "lunch_peak": 1, "afternoon_tea": 2, "dinner_peak": 3, "night_supply_gap": 4}.get(phase, 0)
    return candidates[(offset + phase_bias + int(rng.random() * len(candidates))) % len(candidates)]


def _phase_for_second(second: int) -> str:
    hour = second // 3600
    if hour < 10:
        return "breakfast"
    if hour < 14:
        return "lunch_peak"
    if hour < 17:
        return "afternoon_tea"
    if hour < 21:
        return "dinner_peak"
    return "night_supply_gap"


def _active_shocks(shocks: tuple[DayShock, ...], start_s: int, end_s: int) -> tuple[DayShock, ...]:
    return tuple(shock for shock in shocks if shock.start_s < end_s and shock.end_s > start_s)


def _weather_for_slice(controls: DaySimulationControls, active_shocks: tuple[DayShock, ...], start_s: int) -> str:
    if any(shock.shock_type == "rain_slowdown" for shock in active_shocks):
        return "storm" if controls.weather == "storm" else "rain"
    if controls.weather in {"clear", "rain", "storm", "event"}:
        return controls.weather
    hour = start_s // 3600
    if hour in {15, 16}:
        return "cloudy"
    return "clear"


def _congestion_for_slice(
    controls: DaySimulationControls,
    phase: str,
    active_shocks: tuple[DayShock, ...],
    start_s: int,
) -> float:
    base_by_phase = {
        "breakfast": 0.44,
        "lunch_peak": 0.62,
        "afternoon_tea": 0.38,
        "dinner_peak": 0.68,
        "night_supply_gap": 0.34,
    }
    profile_delta = {"smooth": -0.12, "weekday": 0.0, "rainy": 0.09, "event": 0.16}.get(controls.congestion_profile, 0.0)
    wave = (_stable_unit("congestion", start_s, controls.congestion_profile) - 0.5) * 0.08
    congestion = base_by_phase.get(phase, 0.45) + profile_delta + wave
    for shock in active_shocks:
        if shock.shock_type == "rain_slowdown":
            congestion += shock.severity * 0.16
        elif shock.shock_type == "road_congestion":
            congestion += shock.severity * 0.22
        elif shock.shock_type == "merchant_burst":
            congestion += shock.severity * 0.04
    return round(_clamp(congestion, 0.05, 0.98), 4)


def _courier_supply(couriers: tuple[DayCourier, ...], active_shocks: tuple[DayShock, ...], start_s: int) -> int:
    supply = sum(1 for courier in couriers if courier.shift_start_s <= start_s < courier.shift_end_s)
    for shock in active_shocks:
        if shock.shock_type == "courier_shortage":
            supply = int(round(supply * (1.0 - shock.severity * 0.52)))
    return max(1, supply)


def _priority_for_order(phase: str, weather: str, congestion_level: float, rng: random.Random) -> float:
    phase_boost = {"lunch_peak": 0.14, "dinner_peak": 0.12, "night_supply_gap": 0.10}.get(phase, 0.04)
    weather_boost = {"rain": 0.07, "storm": 0.12, "event": 0.05}.get(weather, 0.0)
    value = 0.38 + phase_boost + weather_boost + congestion_level * 0.18 + rng.random() * 0.18
    return round(_clamp(value, 0.05, 0.98), 4)


def _deadline_window_s(
    phase: str,
    weather: str,
    congestion_level: float,
    priority: float,
    rng: random.Random,
) -> int:
    base_min = {"breakfast": 38, "lunch_peak": 35, "afternoon_tea": 42, "dinner_peak": 37, "night_supply_gap": 45}.get(phase, 40)
    weather_extra = {"rain": 5, "storm": 8, "event": 4}.get(weather, 0)
    tightness = int(priority * 7 + congestion_level * 4 + rng.random() * 5)
    return max(22 * 60, int((base_min + weather_extra - tightness) * 60))


def _destination_for_order(
    scenario: DayScenario,
    merchant_position: Position,
    rng: random.Random,
    phase: str,
) -> Position:
    phase_spread = {"breakfast": 0.22, "lunch_peak": 0.18, "afternoon_tea": 0.16, "dinner_peak": 0.26, "night_supply_gap": 0.31}.get(phase, 0.22)
    lat_span = scenario.map_bounds[1].lat - scenario.map_bounds[0].lat
    lng_span = scenario.map_bounds[1].lng - scenario.map_bounds[0].lng
    lat = merchant_position.lat + (rng.random() - 0.5) * lat_span * phase_spread
    lng = merchant_position.lng + (rng.random() - 0.5) * lng_span * phase_spread
    screen_x = (merchant_position.screen_x or 50.0) + (rng.random() - 0.5) * 34.0 * phase_spread * 3.4
    screen_y = (merchant_position.screen_y or 50.0) + (rng.random() - 0.5) * 34.0 * phase_spread * 3.4
    return _bounded_position(scenario, lat, lng, screen_x, screen_y)


def _risk_tags(
    phase: str,
    weather: str,
    congestion_level: float,
    active_shocks: tuple[DayShock, ...],
    priority: float,
) -> tuple[str, ...]:
    tags = [phase]
    if weather in {"rain", "storm"}:
        tags.append("weather_slowdown")
    if congestion_level >= 0.7:
        tags.append("high_congestion")
    if priority >= 0.72:
        tags.append("tight_deadline")
    for shock in active_shocks:
        tags.append(shock.shock_type)
    return tuple(dict.fromkeys(tags))


def _prep_multiplier(active_shocks: tuple[DayShock, ...], congestion_level: float) -> float:
    multiplier = 1.0 + congestion_level * 0.08
    for shock in active_shocks:
        if shock.shock_type == "merchant_burst":
            multiplier += shock.severity * 0.22
        elif shock.shock_type == "rain_slowdown":
            multiplier += shock.severity * 0.08
    return round(multiplier, 4)


def _world_summary(
    orders: tuple[DayOrder, ...],
    shocks: tuple[DayShock, ...],
    time_slices: tuple[TimeSlice, ...],
    couriers: tuple[DayCourier, ...],
) -> dict[str, Any]:
    phase_counts: dict[str, int] = {}
    for order in orders:
        phase_counts[order.demand_phase] = phase_counts.get(order.demand_phase, 0) + 1
    shock_counts = {shock.shock_type: sum(1 for item in time_slices if shock.id in item.shock_ids) for shock in shocks}
    peak_orders = max((len(item.order_ids) for item in time_slices), default=0)
    min_supply = min((item.courier_supply for item in time_slices), default=0)
    return {
        "total_orders": len(orders),
        "total_couriers": len(couriers),
        "total_time_slices": len(time_slices),
        "phase_counts": phase_counts,
        "shock_slice_counts": shock_counts,
        "peak_orders_per_slice": peak_orders,
        "min_courier_supply": min_supply,
    }


def _zone_position(scenario: DayScenario, zone_id: str, rng: random.Random, spread: float) -> Position:
    anchors = {
        "office_core": (0.45, 0.43),
        "mall_foodcourt": (0.58, 0.36),
        "metro_exit": (0.36, 0.58),
        "residential_edge": (0.68, 0.64),
    }
    anchor_x, anchor_y = anchors.get(zone_id, (0.5, 0.5))
    x_ratio = _clamp(anchor_x + (rng.random() - 0.5) * spread, 0.05, 0.95)
    y_ratio = _clamp(anchor_y + (rng.random() - 0.5) * spread, 0.05, 0.95)
    lat = scenario.map_bounds[0].lat + (scenario.map_bounds[1].lat - scenario.map_bounds[0].lat) * y_ratio
    lng = scenario.map_bounds[0].lng + (scenario.map_bounds[1].lng - scenario.map_bounds[0].lng) * x_ratio
    return Position(
        lat=round(lat, 6),
        lng=round(lng, 6),
        screen_x=round(6.0 + x_ratio * 88.0, 2),
        screen_y=round(92.0 - y_ratio * 84.0, 2),
    )


def _bounded_position(
    scenario: DayScenario,
    lat: float,
    lng: float,
    screen_x: float,
    screen_y: float,
) -> Position:
    min_bound, max_bound = scenario.map_bounds
    return Position(
        lat=round(_clamp(lat, min_bound.lat, max_bound.lat), 6),
        lng=round(_clamp(lng, min_bound.lng, max_bound.lng), 6),
        screen_x=round(_clamp(screen_x, 6.0, 94.0), 2),
        screen_y=round(_clamp(screen_y, 8.0, 92.0), 2),
    )


def _time_slice_id(start_s: int) -> str:
    return f"TS-{start_s // 3600:02d}{(start_s % 3600) // 60:02d}"


def _time_label(start_s: int, phase: str) -> str:
    return f"{start_s // 3600:02d}:{(start_s % 3600) // 60:02d} {phase}"


def _rng(*parts: object) -> random.Random:
    digest = hashlib.sha1("|".join(str(part) for part in parts).encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _stable_unit(*parts: object) -> float:
    digest = hashlib.sha1("|".join(str(part) for part in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") / 0xFFFFFFFF


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
