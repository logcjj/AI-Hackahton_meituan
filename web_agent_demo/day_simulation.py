from __future__ import annotations

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
