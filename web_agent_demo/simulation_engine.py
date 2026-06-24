from __future__ import annotations

import hashlib
import math
import random
from dataclasses import asdict, dataclass, replace
from typing import Any


ENGINE_VERSION = "delivery-simulation-v1"
EARTH_METERS_PER_DEGREE = 111_000.0


@dataclass(frozen=True)
class Position:
    lat: float
    lng: float
    screen_x: float | None = None
    screen_y: float | None = None


@dataclass(frozen=True)
class SimulationControls:
    courier_count: int = 12
    order_intensity: float = 0.62
    burstiness: float = 0.56
    weather: str = "clear"
    congestion_level: float = 0.48
    playback_speed: float = 1.0
    compare_enabled: bool = True

    def normalized(self) -> "SimulationControls":
        return SimulationControls(
            courier_count=max(1, int(self.courier_count)),
            order_intensity=_clamp(float(self.order_intensity), 0.0, 1.0),
            burstiness=_clamp(float(self.burstiness), 0.0, 1.0),
            weather=self.weather if self.weather in {"clear", "rain", "storm", "event"} else "clear",
            congestion_level=_clamp(float(self.congestion_level), 0.0, 1.0),
            playback_speed=_clamp(float(self.playback_speed), 0.25, 8.0),
            compare_enabled=bool(self.compare_enabled),
        )

    def with_patch(self, patch: dict[str, Any] | None) -> "SimulationControls":
        if not patch:
            return self.normalized()
        allowed = set(self.__dataclass_fields__)
        updates = {key: value for key, value in patch.items() if key in allowed}
        return replace(self, **updates).normalized()


@dataclass(frozen=True)
class VisualDirection:
    theme: str
    reference_style: str
    map_treatment: str
    entity_treatment: str
    avoid: tuple[str, ...]


@dataclass(frozen=True)
class SimulationScenario:
    id: str
    name: str
    scene_type: str
    description: str
    map_center: Position
    map_bounds: tuple[Position, Position]
    visual_direction: VisualDirection
    merchant_zones: tuple[str, ...]
    traffic_profiles: tuple[str, ...]
    order_profiles: tuple[str, ...]
    default_controls: SimulationControls


@dataclass(frozen=True)
class SimulationSession:
    session_id: str
    scenario_id: str
    seed: str
    created_at: str
    engine_version: str
    routing_provider: str
    controls: SimulationControls
    status: str = "ready"


@dataclass(frozen=True)
class CourierState:
    id: str
    label: str
    position: Position
    status: str
    capacity: int
    current_order_ids: tuple[str, ...]
    available_at_s: float
    willingness: float
    speed_mps: float
    fatigue: float
    acceptance_bias: float
    route: tuple[Position, ...] = ()


@dataclass(frozen=True)
class MerchantState:
    id: str
    label: str
    position: Position
    pressure: float
    prep_time_s: float
    category: str
    zone_id: str
    pending_order_ids: tuple[str, ...]


@dataclass(frozen=True)
class OrderState:
    id: str
    merchant_id: str
    destination: Position
    created_at_s: float
    deadline_s: float
    priority: float
    status: str
    candidate_courier_ids: tuple[str, ...]
    burst_id: str | None = None


@dataclass(frozen=True)
class CompareTrigger:
    trigger_id: str
    tick_id: str
    reason: str
    active_order_ids: tuple[str, ...]
    time_budget_ms: int
    urgency: float


@dataclass(frozen=True)
class TimelineEvent:
    event_id: str
    session_id: str
    tick_id: str
    sim_time_s: float
    event_type: str
    title: str
    summary: str
    entity_ids: tuple[str, ...]
    severity: str = "info"


@dataclass(frozen=True)
class SimulationTick:
    tick_id: str
    session_id: str
    sim_time_s: float
    map_state: dict[str, Any]
    couriers: tuple[CourierState, ...]
    merchants: tuple[MerchantState, ...]
    orders: tuple[OrderState, ...]
    active_order_ids: tuple[str, ...]
    traffic_state: dict[str, Any]
    trigger_reasons: tuple[str, ...]


@dataclass(frozen=True)
class SimulationStart:
    session: SimulationSession
    tick: SimulationTick
    timeline: tuple[TimelineEvent, ...]


@dataclass(frozen=True)
class SimulationAdvance:
    tick: SimulationTick
    timeline_delta: tuple[TimelineEvent, ...]
    compare_trigger: CompareTrigger | None


def scenario_catalog() -> tuple[SimulationScenario, ...]:
    visual = VisualDirection(
        theme="strategy-sandbox",
        reference_style="simulation-first project map",
        map_treatment="Current project map style with tactical simulation overlays, traffic bands and weather zones.",
        entity_treatment="High-contrast merchant, courier, order burst and congestion markers.",
        avoid=("complex-wireframes", "reasongraph-first-layout", "s1-s5-visual-taxonomy", "static-candidate-table-as-main-story"),
    )
    return (
        SimulationScenario(
            id="commerce_peak",
            name="商圈十字路口高峰",
            scene_type="dense_commerce",
            description="商圈订单密集，适合验证同一时间片内多算法派单对比。",
            map_center=Position(31.2304, 121.4737, 50.0, 50.0),
            map_bounds=(Position(31.2148, 121.4520, 6.0, 92.0), Position(31.2460, 121.4954, 94.0, 8.0)),
            visual_direction=visual,
            merchant_zones=("central_foodcourt", "office_food_street", "mall_edge"),
            traffic_profiles=("normal", "rush", "blocked_crossing"),
            order_profiles=("steady", "lunch_burst", "event_spike"),
            default_controls=SimulationControls(courier_count=14, order_intensity=0.68, burstiness=0.62, weather="clear", congestion_level=0.58),
        ),
        SimulationScenario(
            id="rain_low_willingness",
            name="雨天低接单意愿",
            scene_type="low_willingness",
            description="雨天和低接单意愿叠加，适合验证风险控制和 fallback。",
            map_center=Position(31.2288, 121.4676, 50.0, 50.0),
            map_bounds=(Position(31.2130, 121.4465, 6.0, 92.0), Position(31.2446, 121.4888, 94.0, 8.0)),
            visual_direction=visual,
            merchant_zones=("rain_foodcourt", "metro_exit", "office_cluster"),
            traffic_profiles=("wet_slow", "blocked_crossing", "surge"),
            order_profiles=("steady", "rain_burst"),
            default_controls=SimulationControls(courier_count=12, order_intensity=0.58, burstiness=0.7, weather="rain", congestion_level=0.72),
        ),
        SimulationScenario(
            id="scarce_repair",
            name="骑手稀缺修复",
            scene_type="scarce_couriers",
            description="骑手少于订单压力，适合验证覆盖修复与资源复用风险。",
            map_center=Position(31.2350, 121.4800, 50.0, 50.0),
            map_bounds=(Position(31.2195, 121.4580, 6.0, 92.0), Position(31.2505, 121.5020, 94.0, 8.0)),
            visual_direction=visual,
            merchant_zones=("outer_loop", "remote_food_street", "station_edge"),
            traffic_profiles=("normal", "sparse_supply", "remote_slow"),
            order_profiles=("steady", "remote_burst"),
            default_controls=SimulationControls(courier_count=8, order_intensity=0.64, burstiness=0.48, weather="clear", congestion_level=0.44),
        ),
    )


def get_scenario(scenario_id: str) -> SimulationScenario:
    for scenario in scenario_catalog():
        if scenario.id == scenario_id:
            return scenario
    raise KeyError(f"unknown simulation scenario: {scenario_id}")


def create_simulation_session(
    scenario_id: str = "commerce_peak",
    seed: str = "demo",
    controls: SimulationControls | None = None,
    map_provider: str = "maplibre",
) -> SimulationStart:
    scenario = get_scenario(scenario_id)
    normalized = (controls or scenario.default_controls).normalized()
    session_id = _stable_id("session", scenario_id, seed, normalized.courier_count, normalized.order_intensity, normalized.weather, normalized.congestion_level)
    session = SimulationSession(
        session_id=session_id,
        scenario_id=scenario_id,
        seed=seed,
        created_at=f"sim-seed:{session_id}",
        engine_version=ENGINE_VERSION,
        routing_provider="local-road-graph" if map_provider in {"local-grid", "offline-schematic"} else "local-road-graph",
        controls=normalized,
    )
    tick = _build_initial_tick(scenario, session)
    timeline = (
        TimelineEvent(
            event_id=_stable_id("event", session.session_id, tick.tick_id, "created"),
            session_id=session.session_id,
            tick_id=tick.tick_id,
            sim_time_s=0.0,
            event_type="session_created",
            title="仿真初始化",
            summary=f"{scenario.name} 已初始化：{len(tick.merchants)} 个商家、{len(tick.couriers)} 个骑手。",
            entity_ids=tuple(entity.id for entity in (*tick.merchants, *tick.couriers)),
            severity="info",
        ),
    )
    return SimulationStart(session, tick, timeline)


def advance_simulation(
    session: SimulationSession,
    tick: SimulationTick,
    advance_seconds: int = 20,
    controls_patch: dict[str, Any] | None = None,
    compare_if_due: bool = True,
) -> SimulationAdvance:
    if advance_seconds <= 0:
        raise ValueError("advance_seconds must be positive")
    scenario = get_scenario(session.scenario_id)
    controls = _controls_for_advance(session, tick, controls_patch)
    next_time = tick.sim_time_s + float(advance_seconds)
    existing_orders = list(tick.orders)
    new_orders, order_events, burst_reason = _generate_orders_between(scenario, session, tick, controls, tick.sim_time_s, next_time)
    all_orders = tuple(existing_orders + list(new_orders))
    merchants = _update_merchants_for_orders(tick.merchants, all_orders, controls, next_time)
    resized_couriers, fleet_events = _resize_couriers(scenario, session, tick.couriers, controls, next_time)
    couriers, movement_events = _move_couriers(scenario, session, resized_couriers, merchants, all_orders, controls, tick.sim_time_s, next_time)
    orders = _refresh_order_candidates(all_orders, couriers)
    active_order_ids = tuple(order.id for order in orders if order.status in {"new", "queued"})
    trigger_reasons = _trigger_reasons(burst_reason, new_orders, active_order_ids)
    tick_id = _stable_id("tick", session.session_id, int(next_time), len(orders), controls.weather, controls.congestion_level)
    next_tick = SimulationTick(
        tick_id=tick_id,
        session_id=session.session_id,
        sim_time_s=next_time,
        map_state=_map_state(scenario, controls),
        couriers=couriers,
        merchants=merchants,
        orders=orders,
        active_order_ids=active_order_ids,
        traffic_state=_traffic_state(scenario, controls, next_time),
        trigger_reasons=trigger_reasons,
    )
    timeline = [
        TimelineEvent(
            event_id=_stable_id("event", session.session_id, tick_id, "advanced"),
            session_id=session.session_id,
            tick_id=tick_id,
            sim_time_s=next_time,
            event_type="tick_advanced",
            title="时间推进",
            summary=f"仿真推进到 {int(next_time)} 秒，当前待决策订单 {len(active_order_ids)} 个。",
            entity_ids=active_order_ids,
            severity="info",
        )
    ]
    timeline.extend(order_events)
    timeline.extend(fleet_events)
    timeline.extend(movement_events)
    compare_trigger = _compare_trigger(session, next_tick, burst_reason, controls) if compare_if_due else None
    if compare_trigger is not None:
        timeline.append(
            TimelineEvent(
                event_id=_stable_id("event", session.session_id, tick_id, "compare"),
                session_id=session.session_id,
                tick_id=tick_id,
                sim_time_s=next_time,
                event_type="compare_triggered",
                title="触发实时对比",
                summary=f"{compare_trigger.reason} 触发 {compare_trigger.time_budget_ms}ms 多算法对比。",
                entity_ids=compare_trigger.active_order_ids,
                severity="notice",
            )
        )
    return SimulationAdvance(next_tick, tuple(timeline), compare_trigger)


def simulation_to_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: simulation_to_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [simulation_to_dict(item) for item in value]
    if isinstance(value, list):
        return [simulation_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: simulation_to_dict(item) for key, item in value.items()}
    return value


def _build_initial_tick(scenario: SimulationScenario, session: SimulationSession) -> SimulationTick:
    rng = _rng(session.seed, scenario.id, "initial")
    merchants = tuple(_merchant_state(scenario, rng, index) for index in range(6))
    couriers = tuple(_courier_state(scenario, rng, index, session.controls) for index in range(session.controls.courier_count))
    return SimulationTick(
        tick_id=_stable_id("tick", session.session_id, 0, 0, session.controls.weather, session.controls.congestion_level),
        session_id=session.session_id,
        sim_time_s=0.0,
        map_state=_map_state(scenario, session.controls),
        couriers=couriers,
        merchants=merchants,
        orders=(),
        active_order_ids=(),
        traffic_state=_traffic_state(scenario, session.controls, 0.0),
        trigger_reasons=(),
    )


def _controls_for_advance(
    session: SimulationSession,
    tick: SimulationTick,
    controls_patch: dict[str, Any] | None,
) -> SimulationControls:
    controls = session.controls.with_patch(controls_patch)
    if controls_patch is not None and "courier_count" in controls_patch:
        return controls
    return replace(controls, courier_count=len(tick.couriers)).normalized()


def _merchant_state(scenario: SimulationScenario, rng: random.Random, index: int) -> MerchantState:
    zone = scenario.merchant_zones[index % len(scenario.merchant_zones)]
    position = _position_in_bounds(scenario, rng, 0.34 + (index % 3) * 0.14, 0.30 + (index // 3) * 0.20)
    return MerchantState(
        id=f"M{index + 1:03d}",
        label=f"商家 {index + 1}",
        position=position,
        pressure=round(0.25 + rng.random() * 0.28, 3),
        prep_time_s=round(260 + rng.random() * 260, 1),
        category=("快餐", "茶饮", "小吃", "简餐")[index % 4],
        zone_id=zone,
        pending_order_ids=(),
    )


def _courier_state(scenario: SimulationScenario, rng: random.Random, index: int, controls: SimulationControls) -> CourierState:
    position = _position_in_bounds(scenario, rng, 0.16 + (index % 5) * 0.17, 0.22 + (index // 5) * 0.16)
    willingness_base = 0.42 + rng.random() * 0.38
    weather_penalty = {"clear": 0.0, "rain": 0.10, "storm": 0.18, "event": 0.06}.get(controls.weather, 0.0)
    speed_base = 4.7 - controls.congestion_level * 1.3 - weather_penalty * 4.0
    return CourierState(
        id=f"R{index + 1:03d}",
        label=f"骑手 {index + 1}",
        position=position,
        status="idle",
        capacity=1,
        current_order_ids=(),
        available_at_s=0.0,
        willingness=round(_clamp(willingness_base - weather_penalty, 0.05, 0.98), 4),
        speed_mps=round(max(1.8, speed_base + rng.random() * 0.7), 3),
        fatigue=round(rng.random() * 0.18, 3),
        acceptance_bias=round(rng.uniform(-0.08, 0.08), 4),
    )


def _resize_couriers(
    scenario: SimulationScenario,
    session: SimulationSession,
    couriers: tuple[CourierState, ...],
    controls: SimulationControls,
    sim_time_s: float,
) -> tuple[tuple[CourierState, ...], tuple[TimelineEvent, ...]]:
    target_count = controls.courier_count
    current_count = len(couriers)
    if current_count == target_count:
        return couriers, ()

    if current_count > target_count:
        kept = tuple(couriers[:target_count])
        changed_ids = tuple(courier.id for courier in couriers[target_count:])
    else:
        added: list[CourierState] = []
        for index in range(current_count, target_count):
            rng = _rng(session.seed, scenario.id, "courier-resize", index, int(sim_time_s // 20))
            added.append(_courier_state(scenario, rng, index, controls))
        kept = tuple((*couriers, *added))
        changed_ids = tuple(courier.id for courier in added)

    event = TimelineEvent(
        event_id=_stable_id("event", session.session_id, int(sim_time_s), "fleet_resized", current_count, target_count),
        session_id=session.session_id,
        tick_id=_stable_id("tick-preview", session.session_id, int(sim_time_s)),
        sim_time_s=sim_time_s,
        event_type="fleet_resized",
        title="骑手数量调整",
        summary=f"骑手数量从 {current_count} 调整到 {target_count}。",
        entity_ids=changed_ids,
        severity="notice",
    )
    return kept, (event,)


def _generate_orders_between(
    scenario: SimulationScenario,
    session: SimulationSession,
    tick: SimulationTick,
    controls: SimulationControls,
    start_s: float,
    end_s: float,
) -> tuple[tuple[OrderState, ...], tuple[TimelineEvent, ...], str | None]:
    orders: list[OrderState] = []
    events: list[TimelineEvent] = []
    burst_reason: str | None = None
    next_slot = int(start_s // 20) + 1
    slot_time = next_slot * 20
    while slot_time <= int(end_s + 1e-9):
        is_burst = slot_time % 60 == 0
        base_count = max(1, int(round(controls.order_intensity * 2)))
        burst_extra = int(round(controls.burstiness * 4)) if is_burst else 0
        count = base_count + burst_extra
        burst_id = f"B{slot_time:04d}" if is_burst else None
        if is_burst:
            burst_reason = "order_burst"
        for offset in range(count):
            rng = _rng(session.seed, scenario.id, "order", slot_time, offset, len(tick.orders))
            merchant = tick.merchants[(slot_time // 20 + offset + _stable_int(session.seed, "merchant", offset)) % len(tick.merchants)]
            destination = _destination_for_order(scenario, rng, merchant.position)
            order_id = f"O{int(slot_time):04d}-{offset + 1:02d}"
            order = OrderState(
                id=order_id,
                merchant_id=merchant.id,
                destination=destination,
                created_at_s=float(slot_time),
                deadline_s=float(slot_time + 1800 + int(rng.random() * 720)),
                priority=round(_clamp(0.42 + controls.order_intensity * 0.35 + rng.random() * 0.18, 0.0, 1.0), 3),
                status="new",
                candidate_courier_ids=(),
                burst_id=burst_id,
            )
            orders.append(order)
        event_type = "order_burst" if is_burst else "order_created"
        events.append(
            TimelineEvent(
                event_id=_stable_id("event", session.session_id, slot_time, event_type),
                session_id=session.session_id,
                tick_id=_stable_id("tick-preview", session.session_id, slot_time),
                sim_time_s=float(slot_time),
                event_type=event_type,
                title="订单突发" if is_burst else "商家下单",
                summary=f"{int(slot_time)} 秒生成 {count} 个新订单。",
                entity_ids=tuple(order.id for order in orders[-count:]),
                severity="warning" if is_burst else "notice",
            )
        )
        slot_time += 20
    return tuple(orders), tuple(events), burst_reason


def _destination_for_order(scenario: SimulationScenario, rng: random.Random, merchant_position: Position) -> Position:
    lat_jitter = (rng.random() - 0.5) * 0.018
    lng_jitter = (rng.random() - 0.5) * 0.024
    south_west, north_east = scenario.map_bounds
    lat = _clamp(merchant_position.lat + lat_jitter, south_west.lat, north_east.lat)
    lng = _clamp(merchant_position.lng + lng_jitter, south_west.lng, north_east.lng)
    return _screen_project(scenario, lat, lng)


def _update_merchants_for_orders(
    merchants: tuple[MerchantState, ...],
    orders: tuple[OrderState, ...],
    controls: SimulationControls,
    sim_time_s: float,
) -> tuple[MerchantState, ...]:
    pending_by_merchant: dict[str, list[str]] = {merchant.id: [] for merchant in merchants}
    for order in orders:
        if order.status in {"new", "queued"}:
            pending_by_merchant.setdefault(order.merchant_id, []).append(order.id)
    updated = []
    for merchant in merchants:
        pending = tuple(pending_by_merchant.get(merchant.id, ()))
        pressure = _clamp(0.18 + len(pending) * 0.13 + controls.order_intensity * 0.32 + math.sin(sim_time_s / 90.0) * 0.04, 0.0, 1.0)
        updated.append(replace(merchant, pressure=round(pressure, 3), pending_order_ids=pending))
    return tuple(updated)


def _move_couriers(
    scenario: SimulationScenario,
    session: SimulationSession,
    couriers: tuple[CourierState, ...],
    merchants: tuple[MerchantState, ...],
    orders: tuple[OrderState, ...],
    controls: SimulationControls,
    start_s: float,
    end_s: float,
) -> tuple[tuple[CourierState, ...], tuple[TimelineEvent, ...]]:
    delta_s = max(0.0, end_s - start_s)
    active_merchants = [merchant for merchant in merchants if merchant.pending_order_ids]
    moved: list[CourierState] = []
    moved_ids: list[str] = []
    for index, courier in enumerate(couriers):
        target = _target_for_courier(scenario, session, courier, active_merchants, index, end_s)
        distance_m = _distance_m(courier.position, target)
        traffic_factor = max(0.32, 1.0 - controls.congestion_level * 0.42)
        weather_factor = {"clear": 1.0, "rain": 0.82, "storm": 0.62, "event": 0.74}.get(controls.weather, 1.0)
        travel_m = courier.speed_mps * traffic_factor * weather_factor * delta_s
        next_position = _interpolate_position(scenario, courier.position, target, 0.0 if distance_m == 0 else min(1.0, travel_m / distance_m))
        if _distance_m(courier.position, next_position) > 0.1:
            moved_ids.append(courier.id)
        moved.append(replace(courier, position=next_position, route=(courier.position, next_position)))
    events = ()
    if moved_ids:
        events = (
            TimelineEvent(
                event_id=_stable_id("event", session.session_id, int(end_s), "courier_moved"),
                session_id=session.session_id,
                tick_id=_stable_id("tick-preview", session.session_id, int(end_s)),
                sim_time_s=end_s,
                event_type="courier_moved",
                title="骑手移动",
                summary=f"{len(moved_ids)} 名骑手根据订单压力和巡游策略移动。",
                entity_ids=tuple(moved_ids),
                severity="info",
            ),
        )
    return tuple(moved), events


def _target_for_courier(
    scenario: SimulationScenario,
    session: SimulationSession,
    courier: CourierState,
    active_merchants: list[MerchantState],
    index: int,
    sim_time_s: float,
) -> Position:
    if active_merchants:
        ranked = sorted(active_merchants, key=lambda merchant: (_distance_m(courier.position, merchant.position), merchant.id))
        return ranked[index % min(3, len(ranked))].position
    rng = _rng(session.seed, scenario.id, "patrol", courier.id, int(sim_time_s // 20))
    angle = rng.random() * math.tau
    radius_lat = 0.004 + rng.random() * 0.006
    radius_lng = 0.006 + rng.random() * 0.008
    return _screen_project(
        scenario,
        scenario.map_center.lat + math.sin(angle) * radius_lat,
        scenario.map_center.lng + math.cos(angle) * radius_lng,
    )


def _refresh_order_candidates(orders: tuple[OrderState, ...], couriers: tuple[CourierState, ...]) -> tuple[OrderState, ...]:
    refreshed: list[OrderState] = []
    for order in orders:
        ranked = sorted(couriers, key=lambda courier: (_distance_m(courier.position, order.destination), -courier.willingness, courier.id))
        refreshed.append(replace(order, candidate_courier_ids=tuple(courier.id for courier in ranked[:5])))
    return tuple(refreshed)


def _trigger_reasons(burst_reason: str | None, new_orders: tuple[OrderState, ...], active_order_ids: tuple[str, ...]) -> tuple[str, ...]:
    reasons: list[str] = []
    if burst_reason:
        reasons.append(burst_reason)
    elif new_orders:
        reasons.append("replan")
    if active_order_ids and len(active_order_ids) >= 8:
        reasons.append("courier_shortage")
    return tuple(dict.fromkeys(reasons))


def _compare_trigger(
    session: SimulationSession,
    tick: SimulationTick,
    burst_reason: str | None,
    controls: SimulationControls,
) -> CompareTrigger | None:
    if not controls.compare_enabled or not tick.active_order_ids:
        return None
    reason = burst_reason or ("courier_shortage" if "courier_shortage" in tick.trigger_reasons else "replan")
    if reason not in {"order_burst", "courier_shortage", "weather_shift", "manual_compare", "replan"}:
        return None
    urgency = _clamp(len(tick.active_order_ids) / max(1, len(tick.couriers)) * 0.6 + controls.congestion_level * 0.4, 0.0, 1.0)
    return CompareTrigger(
        trigger_id=_stable_id("trigger", session.session_id, tick.tick_id, reason),
        tick_id=tick.tick_id,
        reason=reason,
        active_order_ids=tick.active_order_ids,
        time_budget_ms=10_000,
        urgency=round(urgency, 3),
    )


def _map_state(scenario: SimulationScenario, controls: SimulationControls) -> dict[str, Any]:
    return {
        "provider": "maplibre",
        "fallback_provider": "offline-schematic",
        "center": simulation_to_dict(scenario.map_center),
        "bounds": [simulation_to_dict(item) for item in scenario.map_bounds],
        "visual_direction": simulation_to_dict(scenario.visual_direction),
        "weather": controls.weather,
        "layers": ["base_map", "merchant_markers", "courier_markers", "order_bursts", "traffic_overlay"],
    }


def _traffic_state(scenario: SimulationScenario, controls: SimulationControls, sim_time_s: float) -> dict[str, Any]:
    pulse = (math.sin(sim_time_s / 120.0) + 1.0) / 2.0
    return {
        "congestion_level": round(_clamp(controls.congestion_level * 0.82 + pulse * 0.18, 0.0, 1.0), 3),
        "weather": controls.weather,
        "profile": scenario.traffic_profiles[min(len(scenario.traffic_profiles) - 1, int(controls.congestion_level * len(scenario.traffic_profiles)))],
    }


def _position_in_bounds(scenario: SimulationScenario, rng: random.Random, x_ratio: float, y_ratio: float) -> Position:
    south_west, north_east = scenario.map_bounds
    lat = south_west.lat + (north_east.lat - south_west.lat) * _clamp(y_ratio + rng.uniform(-0.05, 0.05), 0.05, 0.95)
    lng = south_west.lng + (north_east.lng - south_west.lng) * _clamp(x_ratio + rng.uniform(-0.05, 0.05), 0.05, 0.95)
    return _screen_project(scenario, lat, lng)


def _screen_project(scenario: SimulationScenario, lat: float, lng: float) -> Position:
    south_west, north_east = scenario.map_bounds
    screen_x = (lng - south_west.lng) / max(1e-9, north_east.lng - south_west.lng) * 100.0
    screen_y = 100.0 - (lat - south_west.lat) / max(1e-9, north_east.lat - south_west.lat) * 100.0
    return Position(round(lat, 7), round(lng, 7), round(_clamp(screen_x, 0.0, 100.0), 3), round(_clamp(screen_y, 0.0, 100.0), 3))


def _interpolate_position(scenario: SimulationScenario, start: Position, end: Position, ratio: float) -> Position:
    ratio = _clamp(ratio, 0.0, 1.0)
    return _screen_project(scenario, start.lat + (end.lat - start.lat) * ratio, start.lng + (end.lng - start.lng) * ratio)


def _distance_m(left: Position, right: Position) -> float:
    avg_lat = math.radians((left.lat + right.lat) / 2.0)
    d_lat = (right.lat - left.lat) * EARTH_METERS_PER_DEGREE
    d_lng = (right.lng - left.lng) * EARTH_METERS_PER_DEGREE * math.cos(avg_lat)
    return math.hypot(d_lat, d_lng)


def _stable_id(*parts: object) -> str:
    return hashlib.sha1("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]


def _stable_int(*parts: object) -> int:
    return int(hashlib.sha1("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:12], 16)


def _rng(*parts: object) -> random.Random:
    return random.Random(_stable_int(*parts))


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
