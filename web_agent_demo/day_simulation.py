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


@dataclass(frozen=True)
class _AssignmentRecord:
    assignment: DispatchAssignment
    slice_id: str
    created_at_s: int
    finish_at_s: float
    distance_m: float
    courier_busy_s: float
    basket_value_yuan: float
    late: bool


@dataclass(frozen=True)
class _AlgorithmSimulationResult:
    algorithm_id: str
    label: str
    family: str
    metrics: DayMetrics
    frame_ids: tuple[str, ...]
    records_by_slice: dict[str, tuple[_AssignmentRecord, ...]]
    metrics_by_slice: dict[str, DayMetrics]
    completed_by_slice: dict[str, tuple[str, ...]]
    courier_positions_by_slice: dict[str, tuple[dict[str, Any], ...]]
    route_overlays_by_slice: dict[str, tuple[dict[str, Any], ...]]
    summary_by_slice: dict[str, str]


@dataclass
class _CourierPlan:
    courier: DayCourier
    position: Position
    available_at_s: float
    busy_time_s: float = 0.0
    assigned_count: int = 0


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


def run_full_day_comparison(
    scenario_id: str = "weekday_full_day",
    seed: str = "demo",
    controls: DaySimulationControls | None = None,
    world: DaySimulationWorld | None = None,
) -> DaySimulationContract:
    day_world = world or generate_full_day_world(scenario_id=scenario_id, seed=seed, controls=controls)
    baseline = _simulate_day_algorithm(day_world, day_world.controls.baseline_algorithm_id)
    challenger = _simulate_day_algorithm(day_world, day_world.controls.challenger_algorithm_id)
    frames, reasoning_traces = _build_comparison_frames(day_world, baseline, challenger)
    return DaySimulationContract(
        contract_version=DAY_SIMULATION_CONTRACT_VERSION,
        scenario=day_world.scenario,
        merchants=day_world.merchants,
        couriers=day_world.couriers,
        orders=day_world.orders,
        shocks=day_world.shocks,
        time_slices=day_world.time_slices,
        baseline_run=_algorithm_day_run(day_world, baseline, frames, reasoning_traces),
        challenger_run=_algorithm_day_run(day_world, challenger, frames, reasoning_traces),
        frames=frames,
        reasoning_traces=reasoning_traces,
        evolution_events=(),
        api_endpoints=dict(DAY_SIMULATION_ENDPOINTS),
        privacy={
            "llm_api_key": "env-only",
            "llm_base_url": "env-only",
            "llm_model": "env-only",
            "secret_handling": "env-only-redacted",
        },
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


def day_comparison_to_dict(value: Any) -> Any:
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


def _simulate_day_algorithm(world: DaySimulationWorld, algorithm_id: str) -> _AlgorithmSimulationResult:
    label, family = _algorithm_label_family(algorithm_id)
    courier_plans = {courier.id: _CourierPlan(courier=courier, position=courier.start_position, available_at_s=courier.shift_start_s) for courier in world.couriers}
    order_by_id = {order.id: order for order in world.orders}
    records_by_slice: dict[str, list[_AssignmentRecord]] = {time_slice.id: [] for time_slice in world.time_slices}
    metrics_by_slice: dict[str, DayMetrics] = {}
    completed_by_slice: dict[str, tuple[str, ...]] = {}
    courier_positions_by_slice: dict[str, tuple[dict[str, Any], ...]] = {}
    route_overlays_by_slice: dict[str, tuple[dict[str, Any], ...]] = {}
    summary_by_slice: dict[str, str] = {}
    cumulative_records: list[_AssignmentRecord] = []
    all_records: list[_AssignmentRecord] = []

    for time_slice in world.time_slices:
        slice_records: list[_AssignmentRecord] = []
        for order_id in time_slice.order_ids:
            record = _assign_order(time_slice, order_by_id[order_id], courier_plans, algorithm_id)
            plan = courier_plans[record.assignment.courier_id]
            plan.position = order_by_id[order_id].destination
            plan.available_at_s = record.finish_at_s
            plan.busy_time_s += record.courier_busy_s
            plan.assigned_count += 1
            slice_records.append(record)
            all_records.append(record)
        cumulative_records.extend(slice_records)
        records_by_slice[time_slice.id] = slice_records
        metrics_by_slice[time_slice.id] = _metrics_from_records(cumulative_records, world, courier_plans)
        completed_by_slice[time_slice.id] = tuple(record.assignment.order_id for record in cumulative_records if record.finish_at_s <= time_slice.end_s)
        courier_positions_by_slice[time_slice.id] = _courier_position_snapshots(courier_plans, time_slice.end_s)
        route_overlays_by_slice[time_slice.id] = tuple(
            _record_route_overlay(record, order_by_id[record.assignment.order_id], algorithm_id) for record in slice_records[:8]
        )
        summary_by_slice[time_slice.id] = _slice_decision_summary(algorithm_id, slice_records)

    frame_ids = tuple(_frame_id(time_slice.id) for time_slice in world.time_slices if _should_emit_frame(time_slice, records_by_slice[time_slice.id]))
    return _AlgorithmSimulationResult(
        algorithm_id=algorithm_id,
        label=label,
        family=family,
        metrics=_metrics_from_records(all_records, world, courier_plans),
        frame_ids=frame_ids,
        records_by_slice={key: tuple(value) for key, value in records_by_slice.items()},
        metrics_by_slice=metrics_by_slice,
        completed_by_slice=completed_by_slice,
        courier_positions_by_slice=courier_positions_by_slice,
        route_overlays_by_slice=route_overlays_by_slice,
        summary_by_slice=summary_by_slice,
    )


def _assign_order(
    time_slice: TimeSlice,
    order: DayOrder,
    courier_plans: dict[str, _CourierPlan],
    algorithm_id: str,
) -> _AssignmentRecord:
    candidates = tuple(plan for plan in courier_plans.values() if plan.courier.shift_start_s <= order.created_at_s < plan.courier.shift_end_s)
    if not candidates:
        candidates = tuple(courier_plans.values())
    profiles = tuple(_assignment_profile(time_slice, order, plan, algorithm_id) for plan in candidates)
    if algorithm_id == "nearest_greedy":
        profile = min(profiles, key=lambda item: (item["pickup_distance_m"], item["courier_available_at_s"], item["courier_id"]))
        rationale = "Nearest greedy selected the closest courier to the merchant and ignored future availability risk."
    elif algorithm_id == "cost_greedy":
        profile = min(profiles, key=lambda item: (item["expected_cost_yuan"], item["finish_at_s"], item["courier_id"]))
        rationale = "Cost greedy minimized immediate fulfillment cost without learning from scenario pressure."
    else:
        profile = min(profiles, key=lambda item: (item["autosolver_score"], item["timeout_risk"], item["finish_at_s"], item["courier_id"]))
        rationale = "AutoSolver balanced availability, congestion, deadline risk and courier load on the same order stream."
    assignment = DispatchAssignment(
        order_id=order.id,
        courier_id=str(profile["courier_id"]),
        merchant_id=order.merchant_id,
        pickup_eta_s=round(float(profile["pickup_eta_s"]), 3),
        delivery_eta_s=round(float(profile["delivery_eta_s"]), 3),
        total_eta_s=round(float(profile["total_eta_s"]), 3),
        expected_cost_yuan=round(float(profile["expected_cost_yuan"]), 3),
        timeout_risk=round(float(profile["timeout_risk"]), 4),
        rationale=rationale,
    )
    return _AssignmentRecord(
        assignment=assignment,
        slice_id=time_slice.id,
        created_at_s=order.created_at_s,
        finish_at_s=round(float(profile["finish_at_s"]), 3),
        distance_m=round(float(profile["total_distance_m"]), 3),
        courier_busy_s=round(float(profile["courier_busy_s"]), 3),
        basket_value_yuan=order.basket_value_yuan,
        late=bool(profile["late"]),
    )


def _assignment_profile(
    time_slice: TimeSlice,
    order: DayOrder,
    plan: _CourierPlan,
    algorithm_id: str,
) -> dict[str, float | str | bool]:
    pickup_distance = _distance_m(plan.position, order.merchant_position)
    delivery_distance = _distance_m(order.merchant_position, order.destination)
    routing_factor = _routing_factor(algorithm_id, time_slice, order)
    pickup_distance *= routing_factor
    delivery_distance *= routing_factor
    total_distance = pickup_distance + delivery_distance
    speed = _effective_speed_mps(plan.courier, time_slice, algorithm_id)
    pickup_eta = pickup_distance / speed
    delivery_eta = delivery_distance / speed
    start_at = max(float(order.created_at_s), plan.available_at_s)
    wait_for_courier = max(0.0, start_at - order.created_at_s)
    prep_wait = max(0.0, order.prep_time_s - pickup_eta)
    finish_at = start_at + pickup_eta + prep_wait + delivery_eta
    total_eta = finish_at - order.created_at_s
    timeout_risk = _timeout_risk(order, time_slice, finish_at, algorithm_id)
    expected_cost = _expected_cost_yuan(total_distance, wait_for_courier, timeout_risk, order, algorithm_id)
    load_penalty = plan.assigned_count * 38.0
    future_pressure = len(time_slice.order_ids) / max(1.0, time_slice.courier_supply)
    autosolver_score = finish_at + timeout_risk * 1800.0 + expected_cost * 35.0 + load_penalty + future_pressure * 160.0
    if algorithm_id == "nearest_greedy":
        autosolver_score = pickup_distance
    return {
        "courier_id": plan.courier.id,
        "courier_available_at_s": plan.available_at_s,
        "pickup_distance_m": pickup_distance,
        "total_distance_m": total_distance,
        "pickup_eta_s": pickup_eta + wait_for_courier,
        "delivery_eta_s": delivery_eta + prep_wait,
        "total_eta_s": total_eta,
        "finish_at_s": finish_at,
        "expected_cost_yuan": expected_cost,
        "timeout_risk": timeout_risk,
        "courier_busy_s": pickup_eta + prep_wait + delivery_eta,
        "late": finish_at > order.deadline_s,
        "autosolver_score": autosolver_score,
    }


def _build_comparison_frames(
    world: DaySimulationWorld,
    baseline: _AlgorithmSimulationResult,
    challenger: _AlgorithmSimulationResult,
) -> tuple[tuple[SideBySideFrame, ...], tuple[ReasoningTrace, ...]]:
    frames: list[SideBySideFrame] = []
    traces: list[ReasoningTrace] = []
    for time_slice in world.time_slices:
        baseline_records = baseline.records_by_slice.get(time_slice.id, ())
        if not _should_emit_frame(time_slice, baseline_records):
            continue
        challenger_records = challenger.records_by_slice.get(time_slice.id, ())
        baseline_metrics = baseline.metrics_by_slice[time_slice.id]
        challenger_metrics = challenger.metrics_by_slice[time_slice.id]
        delta = _metric_delta(baseline_metrics, challenger_metrics)
        frame_id = _frame_id(time_slice.id)
        trace_id = f"RT-{frame_id}"
        frame = SideBySideFrame(
            id=frame_id,
            scenario_id=world.scenario.id,
            time_slice_id=time_slice.id,
            sim_time_s=time_slice.start_s,
            baseline=_algorithm_frame(baseline, time_slice, baseline_records),
            challenger=_algorithm_frame(challenger, time_slice, challenger_records),
            delta=delta,
            highlighted_order_ids=_highlighted_order_ids(baseline_records, challenger_records),
            highlighted_courier_ids=_highlighted_courier_ids(baseline_records, challenger_records),
            reasoning_trace_ids=(trace_id,),
            memory_event_ids=(),
        )
        frames.append(frame)
        traces.append(_reasoning_trace(frame, time_slice, baseline, challenger, delta))
    return tuple(frames), tuple(traces)


def _algorithm_frame(
    result: _AlgorithmSimulationResult,
    time_slice: TimeSlice,
    records: tuple[_AssignmentRecord, ...],
) -> AlgorithmFrame:
    return AlgorithmFrame(
        algorithm_id=result.algorithm_id,
        label=result.label,
        status="selected" if result.algorithm_id == "autosolver_agent" else "evaluated",
        courier_positions=result.courier_positions_by_slice[time_slice.id],
        active_order_ids=time_slice.order_ids,
        completed_order_ids=result.completed_by_slice[time_slice.id],
        assignments=tuple(record.assignment for record in records),
        route_overlays=result.route_overlays_by_slice[time_slice.id],
        metrics=result.metrics_by_slice[time_slice.id],
        decision_summary=result.summary_by_slice[time_slice.id],
    )


def _reasoning_trace(
    frame: SideBySideFrame,
    time_slice: TimeSlice,
    baseline: _AlgorithmSimulationResult,
    challenger: _AlgorithmSimulationResult,
    delta: MetricDelta,
) -> ReasoningTrace:
    baseline_metrics = frame.baseline.metrics
    challenger_metrics = frame.challenger.metrics
    selected = "adaptive_risk_balanced_dispatch" if delta.time_saved_s >= 0 else "fallback_to_baseline_guardrail"
    return ReasoningTrace(
        id=frame.reasoning_trace_ids[0],
        frame_id=frame.id,
        algorithm_id=challenger.algorithm_id,
        selected_strategy=selected,
        candidate_scores=(
            AlgorithmCandidateScore(
                algorithm_id=baseline.algorithm_id,
                score=round(_candidate_score(baseline_metrics), 4),
                estimated_runtime_ms=round(8.0 + len(time_slice.order_ids) * 0.7, 3),
                expected_time_cost_s=baseline_metrics.total_time_cost_s,
                expected_cost_yuan=baseline_metrics.total_cost_yuan,
                risk_score=baseline_metrics.timeout_risk,
                reason="Baseline optimizes nearest pickup, so queueing and deadline risk can accumulate.",
            ),
            AlgorithmCandidateScore(
                algorithm_id=challenger.algorithm_id,
                score=round(_candidate_score(challenger_metrics), 4),
                estimated_runtime_ms=round(180.0 + len(time_slice.order_ids) * 5.5, 3),
                expected_time_cost_s=challenger_metrics.total_time_cost_s,
                expected_cost_yuan=challenger_metrics.total_cost_yuan,
                risk_score=challenger_metrics.timeout_risk,
                reason="AutoSolver evaluates availability, congestion, route cost and deadline pressure.",
            ),
        ),
        evidence={
            "time_slice_id": time_slice.id,
            "demand_phase": time_slice.demand_phase,
            "weather": time_slice.weather,
            "congestion_level": time_slice.congestion_level,
            "order_count": len(time_slice.order_ids),
            "courier_supply": time_slice.courier_supply,
            "shock_ids": time_slice.shock_ids,
        },
        rationale=_reasoning_rationale(time_slice, delta),
        expected_impact=delta,
        time_budget_ms=10_000,
        memory_event_ids=(),
    )


def _algorithm_day_run(
    world: DaySimulationWorld,
    result: _AlgorithmSimulationResult,
    frames: tuple[SideBySideFrame, ...],
    traces: tuple[ReasoningTrace, ...],
) -> AlgorithmDayRun:
    trace_ids = tuple(trace.id for trace in traces) if result.algorithm_id == world.controls.challenger_algorithm_id else ()
    return AlgorithmDayRun(
        run_id=f"DAY-RUN-{result.algorithm_id}-{world.seed}",
        scenario_id=world.scenario.id,
        algorithm_id=result.algorithm_id,
        label=result.label,
        family=result.family,
        status="completed",
        metrics=result.metrics,
        frame_ids=tuple(frame.id for frame in frames),
        decision_trace_ids=trace_ids,
        memory_event_ids=(),
        summary=_run_summary(result),
    )


def _metrics_from_records(
    records: list[_AssignmentRecord],
    world: DaySimulationWorld,
    courier_plans: dict[str, _CourierPlan],
) -> DayMetrics:
    total_orders = len(world.orders)
    assigned = len(records)
    delivered = sum(1 for record in records if record.finish_at_s <= world.scenario.day_end_s)
    late = sum(1 for record in records if record.late)
    eta_values = sorted(record.assignment.total_eta_s for record in records)
    avg_eta = sum(eta_values) / len(eta_values) if eta_values else 0.0
    p95_eta = eta_values[min(len(eta_values) - 1, int(len(eta_values) * 0.95))] if eta_values else 0.0
    total_time = sum(record.assignment.total_eta_s for record in records)
    total_distance = sum(record.distance_m for record in records)
    total_cost = sum(record.assignment.expected_cost_yuan for record in records)
    timeout_risk = sum(record.assignment.timeout_risk for record in records) / len(records) if records else 0.0
    day_duration = max(1, world.scenario.day_end_s - world.scenario.day_start_s)
    utilization = sum(plan.busy_time_s for plan in courier_plans.values()) / max(1.0, len(courier_plans) * day_duration)
    revenue = sum(record.basket_value_yuan for record in records)
    return DayMetrics(
        total_orders=total_orders,
        delivered_orders=delivered,
        assigned_orders=assigned,
        late_orders=late,
        coverage_rate=round(assigned / max(1, total_orders), 4),
        avg_eta_s=round(avg_eta, 3),
        p95_eta_s=round(p95_eta, 3),
        total_time_cost_s=round(total_time, 3),
        total_distance_m=round(total_distance, 3),
        total_cost_yuan=round(total_cost, 3),
        timeout_risk=round(timeout_risk, 4),
        courier_utilization=round(_clamp(utilization, 0.0, 1.0), 4),
        gross_revenue_yuan=round(revenue, 3),
    )


def _metric_delta(baseline: DayMetrics, challenger: DayMetrics) -> MetricDelta:
    time_saved = round(baseline.total_time_cost_s - challenger.total_time_cost_s, 3)
    cost_saved = round(baseline.total_cost_yuan - challenger.total_cost_yuan, 3)
    headline = f"AutoSolver saves {time_saved / 60.0:.1f} minutes and {cost_saved:.1f} yuan cumulatively."
    if time_saved < 0 or cost_saved < 0:
        headline = "AutoSolver exposes a guardrail case where baseline remains competitive."
    return MetricDelta(
        time_saved_s=time_saved,
        cost_saved_yuan=cost_saved,
        extra_delivered_orders=challenger.delivered_orders - baseline.delivered_orders,
        timeout_risk_delta=round(challenger.timeout_risk - baseline.timeout_risk, 4),
        utilization_delta=round(challenger.courier_utilization - baseline.courier_utilization, 4),
        headline=headline,
    )


def _algorithm_label_family(algorithm_id: str) -> tuple[str, str]:
    labels = {
        "nearest_greedy": ("Pure Greedy", "baseline"),
        "cost_greedy": ("Cost Greedy", "greedy"),
        "autosolver_agent": ("AutoSolver Agent", "agent"),
    }
    return labels.get(algorithm_id, (algorithm_id.replace("_", " ").title(), "agent" if "agent" in algorithm_id else "advanced"))


def _effective_speed_mps(courier: DayCourier, time_slice: TimeSlice, algorithm_id: str) -> float:
    congestion_drag = time_slice.congestion_level * (0.42 if algorithm_id == "nearest_greedy" else 0.32)
    weather_drag = {"rain": 0.10, "storm": 0.18, "event": 0.08}.get(time_slice.weather, 0.0)
    load_factor = 0.92 + courier.willingness * 0.14
    speed = courier.base_speed_mps * max(0.42, 1.0 - congestion_drag - weather_drag) * load_factor
    if algorithm_id == "autosolver_agent":
        speed *= 1.06
    return max(1.25, speed)


def _routing_factor(algorithm_id: str, time_slice: TimeSlice, order: DayOrder) -> float:
    if algorithm_id == "nearest_greedy":
        return 1.0
    factor = 0.96 - time_slice.congestion_level * 0.08
    if "weather_slowdown" in order.risk_tags:
        factor -= 0.035
    if "road_congestion" in order.risk_tags:
        factor -= 0.035
    return _clamp(factor, 0.82, 1.02)


def _timeout_risk(order: DayOrder, time_slice: TimeSlice, finish_at_s: float, algorithm_id: str) -> float:
    slack_s = order.deadline_s - finish_at_s
    if slack_s >= 0:
        pressure = 1.0 / (1.0 + min(3600.0, slack_s) / 900.0)
    else:
        pressure = 0.82 + min(0.16, abs(slack_s) / 3600.0)
    risk = 0.08 + time_slice.congestion_level * 0.18 + order.priority * 0.12 + pressure * 0.34
    if algorithm_id == "autosolver_agent":
        risk *= 0.78
    return round(_clamp(risk, 0.02, 0.98), 4)


def _expected_cost_yuan(
    distance_m: float,
    wait_for_courier_s: float,
    timeout_risk: float,
    order: DayOrder,
    algorithm_id: str,
) -> float:
    distance_cost = distance_m / 1000.0 * 2.35
    wait_cost = wait_for_courier_s / 60.0 * 0.18
    risk_cost = timeout_risk * order.penalty_yuan
    efficiency = 0.94 if algorithm_id == "autosolver_agent" else 1.0
    return round((distance_cost + wait_cost + risk_cost + 2.8) * efficiency, 4)


def _courier_position_snapshots(courier_plans: dict[str, _CourierPlan], sim_time_s: int) -> tuple[dict[str, Any], ...]:
    ranked = sorted(courier_plans.values(), key=lambda plan: (-plan.assigned_count, plan.courier.id))[:24]
    return tuple(
        {
            "courier_id": plan.courier.id,
            "label": plan.courier.label,
            "position": simulation_to_dict(plan.position),
            "status": "busy" if plan.available_at_s > sim_time_s else "available",
            "available_at_s": round(plan.available_at_s, 3),
            "assigned_count": plan.assigned_count,
        }
        for plan in ranked
    )


def _record_route_overlay(record: _AssignmentRecord, order: DayOrder, algorithm_id: str) -> dict[str, Any]:
    return {
        "lane": "challenger" if algorithm_id == "autosolver_agent" else "baseline",
        "order_id": order.id,
        "courier_id": record.assignment.courier_id,
        "polyline": [
            simulation_to_dict(order.merchant_position),
            simulation_to_dict(order.destination),
        ],
        "eta_s": record.assignment.total_eta_s,
        "cost_yuan": record.assignment.expected_cost_yuan,
    }


def _slice_decision_summary(algorithm_id: str, records: list[_AssignmentRecord]) -> str:
    if not records:
        return "No orders in this time slice."
    avg_eta = sum(record.assignment.total_eta_s for record in records) / len(records)
    if algorithm_id == "nearest_greedy":
        return f"Nearest greedy assigned {len(records)} orders by pickup distance; avg ETA {avg_eta / 60.0:.1f} min."
    if algorithm_id == "autosolver_agent":
        return f"AutoSolver assigned {len(records)} orders with risk-aware availability scoring; avg ETA {avg_eta / 60.0:.1f} min."
    return f"{algorithm_id} assigned {len(records)} orders; avg ETA {avg_eta / 60.0:.1f} min."


def _should_emit_frame(time_slice: TimeSlice, records: tuple[_AssignmentRecord, ...] | list[_AssignmentRecord]) -> bool:
    return bool(records) and (time_slice.compare_due or time_slice.demand_phase in {"lunch_peak", "dinner_peak", "night_supply_gap"})


def _frame_id(time_slice_id: str) -> str:
    return f"F-{time_slice_id}"


def _highlighted_order_ids(
    baseline_records: tuple[_AssignmentRecord, ...],
    challenger_records: tuple[_AssignmentRecord, ...],
) -> tuple[str, ...]:
    by_challenger = {record.assignment.order_id: record for record in challenger_records}
    ranked = sorted(
        (
            (base.assignment.total_eta_s - by_challenger[base.assignment.order_id].assignment.total_eta_s, base.assignment.order_id)
            for base in baseline_records
            if base.assignment.order_id in by_challenger
        ),
        reverse=True,
    )
    return tuple(order_id for _, order_id in ranked[:6])


def _highlighted_courier_ids(
    baseline_records: tuple[_AssignmentRecord, ...],
    challenger_records: tuple[_AssignmentRecord, ...],
) -> tuple[str, ...]:
    courier_ids = []
    for base, challenger in zip(baseline_records, challenger_records):
        if base.assignment.courier_id != challenger.assignment.courier_id:
            courier_ids.extend([base.assignment.courier_id, challenger.assignment.courier_id])
        if len(courier_ids) >= 8:
            break
    return tuple(dict.fromkeys(courier_ids))


def _candidate_score(metrics: DayMetrics) -> float:
    if metrics.assigned_orders == 0:
        return 0.0
    penalty = metrics.avg_eta_s / 2400.0 + metrics.timeout_risk * 1.8 + metrics.total_cost_yuan / max(1.0, metrics.gross_revenue_yuan) * 0.45
    return _clamp(1.0 - penalty, 0.0, 1.0)


def _reasoning_rationale(time_slice: TimeSlice, delta: MetricDelta) -> str:
    if delta.time_saved_s >= 0 and delta.cost_saved_yuan >= 0:
        return (
            f"In {time_slice.id}, AutoSolver uses supply, congestion and deadline pressure to reduce cumulative "
            f"time by {delta.time_saved_s / 60.0:.1f} minutes and cost by {delta.cost_saved_yuan:.1f} yuan."
        )
    return f"In {time_slice.id}, the comparator flags a guardrail case where greedy remains close on immediate cost."


def _run_summary(result: _AlgorithmSimulationResult) -> str:
    metrics = result.metrics
    return (
        f"{result.label} assigned {metrics.assigned_orders}/{metrics.total_orders} orders, "
        f"avg ETA {metrics.avg_eta_s / 60.0:.1f} min, total cost {metrics.total_cost_yuan:.1f} yuan."
    )


def _distance_m(left: Position, right: Position) -> float:
    lat_m = (left.lat - right.lat) * 111_000.0
    lng_m = (left.lng - right.lng) * 111_000.0
    return (lat_m * lat_m + lng_m * lng_m) ** 0.5


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
