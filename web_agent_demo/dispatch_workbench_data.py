from __future__ import annotations

from typing import Any

from web_agent_demo.day_simulation import DaySimulationContract


WORKBENCH_MODEL_VERSION = "dispatch-workbench-v1"


def build_dispatch_workbench_payload(contract: DaySimulationContract) -> dict[str, Any]:
    """Normalize the day-simulation contract into a route-level workbench model."""

    merchants_by_id = {merchant.id: merchant for merchant in contract.merchants}
    couriers_by_id = {courier.id: courier for courier in contract.couriers}
    orders_by_id = {order.id: order for order in contract.orders}
    slices_by_id = {time_slice.id: time_slice for time_slice in contract.time_slices}
    frames_by_id = {frame.id: frame for frame in contract.frames}
    trace_by_frame_id = {trace.frame_id: trace for trace in contract.reasoning_traces}
    memory_by_id = {event.id: event for event in contract.evolution_events}
    frame_by_order_id = _frame_by_order_id(contract)
    baseline_assignments = _assignment_lookup(contract, lane="baseline")
    challenger_assignments = _assignment_lookup(contract, lane="challenger")

    orders = [
        _order_payload(
            order=order,
            merchant=merchants_by_id[order.merchant_id],
            frame=frame_by_order_id.get(order.id),
            baseline_assignment=baseline_assignments.get(order.id),
            challenger_assignment=challenger_assignments.get(order.id),
        )
        for order in sorted(contract.orders, key=lambda item: (item.created_at_s, item.id))
    ]
    riders = [
        _rider_payload(
            courier=courier,
            challenger_assignments=challenger_assignments,
            orders_by_id=orders_by_id,
            frames=contract.frames,
        )
        for courier in sorted(contract.couriers, key=lambda item: item.id)
    ]
    decisions = [
        _decision_payload(
            frame=frame,
            trace=trace_by_frame_id.get(frame.id),
            time_slice=slices_by_id[frame.time_slice_id],
            orders_by_id=orders_by_id,
            couriers_by_id=couriers_by_id,
            memory_by_id=memory_by_id,
        )
        for frame in contract.frames
    ]
    memories = [
        _memory_payload(
            event=event,
            frame=frames_by_id[event.frame_id],
            time_slice=slices_by_id[frames_by_id[event.frame_id].time_slice_id],
            decision_id=f"D-{event.frame_id}",
        )
        for event in contract.evolution_events
    ]
    memory_sections = _memory_sections(memories)

    final_frame = contract.frames[-1]
    return {
        "model_version": WORKBENCH_MODEL_VERSION,
        "source": {
            "product_reference": "Kandbox Dispatch public live/docs/client structure",
            "contract_version": contract.contract_version,
            "scenario_id": contract.scenario.id,
            "scenario_name": contract.scenario.name,
            "day_start_s": contract.scenario.day_start_s,
            "day_end_s": contract.scenario.day_end_s,
            "generated_at": "deterministic-contract-build",
        },
        "routes": [
            {"id": "live", "path": "#/live", "label": "实时推理", "kandbox_module": "Live Map"},
            {"id": "decisions", "path": "#/decisions", "label": "决策链路", "kandbox_module": "Planner / Chart"},
            {"id": "memory", "path": "#/memory", "label": "长期记忆", "kandbox_module": "History / assistance"},
            {"id": "orders", "path": "#/orders", "label": "订单输入", "kandbox_module": "Jobs / Orders"},
            {"id": "riders", "path": "#/riders", "label": "运力资源", "kandbox_module": "Workers"},
        ],
        "entities": {
            "orders": orders,
            "riders": riders,
            "merchants": [_merchant_payload(merchant) for merchant in sorted(contract.merchants, key=lambda item: item.id)],
            "shocks": [_shock_payload(shock) for shock in contract.shocks],
        },
        "map": {
            "provider": contract.scenario.map_provider,
            "tile_provider": "cartodb-light-nolabels-leaflet",
            "center": _position_payload(contract.scenario.map_center),
            "bounds": [_position_payload(item) for item in contract.scenario.map_bounds],
            "anchors": _map_anchors(contract),
            "aliases": _map_aliases(contract),
            "hotspots": _hotspots(contract),
            "routes": _route_payloads(contract),
            "privacy": {
                "entity_labels": "anonymized",
                "road_labels": "hidden_by_default",
                "label_schema": "M-01 / R-01 / O-001",
            },
        },
        "timeline": {
            "start_s": contract.scenario.day_start_s,
            "end_s": contract.scenario.day_end_s,
            "time_slices": [_time_slice_payload(item) for item in contract.time_slices],
            "events": _timeline_events(contract, orders_by_id, memory_by_id),
        },
        "metrics": {
            "baseline_algorithm": contract.baseline_run.algorithm_id,
            "challenger_algorithm": contract.challenger_run.algorithm_id,
            "final": _scorecard_payload(final_frame),
            "series": [_scorecard_payload(frame) for frame in contract.frames],
        },
        "decisions": decisions,
        "memory": {
            "items": memories,
            "sections": memory_sections,
            "system": _memory_system(memories),
            "layers": _memory_layers(memories, memory_sections),
            "profiles": _memory_profiles(memories, memory_sections),
            "recall_chain": _memory_recall_chain(memories, memory_sections),
            "writeback_loop": _memory_writeback_loop(memories, memory_sections),
        },
        "filters": {
            "order_time_bands": _order_time_bands(contract),
            "areas": sorted(contract.scenario.merchant_zones),
            "statuses": ["scheduled", "entered_inference", "assigned", "delivered", "late_risk"],
            "risk_levels": ["low", "medium", "high"],
            "rider_states": ["offline", "available", "busy", "ending_shift"],
        },
        "inspection": {
            "order_count": len(orders),
            "rider_count": len(riders),
            "decision_count": len(decisions),
            "memory_count": len(memories),
            "event_count": len(_timeline_events(contract, orders_by_id, memory_by_id)),
            "full_day_preloaded": True,
            "deterministic": True,
        },
    }


def _order_payload(
    order: Any,
    merchant: Any,
    frame: Any | None,
    baseline_assignment: dict[str, Any] | None,
    challenger_assignment: dict[str, Any] | None,
) -> dict[str, Any]:
    risk_level = _risk_level(order)
    entered_inference = frame is not None
    status = "assigned" if challenger_assignment else "scheduled"
    if risk_level == "high" and not challenger_assignment:
        status = "late_risk"
    return {
        "id": order.id,
        "merchant_id": order.merchant_id,
        "merchant_label": merchant.label,
        "pickup_label": f"{merchant.label} pickup",
        "created_at_s": order.created_at_s,
        "created_at_label": _clock(order.created_at_s),
        "promised_at_s": order.deadline_s,
        "promised_at_label": _clock(order.deadline_s),
        "status": status,
        "risk_level": risk_level,
        "risk_tags": list(order.risk_tags),
        "business_area": merchant.zone_id,
        "demand_phase": order.demand_phase,
        "entered_inference": entered_inference,
        "frame_id": frame.id if frame else "",
        "basket_value_yuan": order.basket_value_yuan,
        "penalty_yuan": order.penalty_yuan,
        "pickup_position": _position_payload(order.merchant_position),
        "dropoff_position": _position_payload(order.destination),
        "baseline_result": _algorithm_result_payload(baseline_assignment, fallback_algorithm="nearest_greedy"),
        "our_result": _algorithm_result_payload(challenger_assignment, fallback_algorithm="autosolver_agent"),
    }


def _rider_payload(
    courier: Any,
    challenger_assignments: dict[str, dict[str, Any]],
    orders_by_id: dict[str, Any],
    frames: tuple[Any, ...],
) -> dict[str, Any]:
    task_chain = [
        {
            "order_id": assignment["order_id"],
            "merchant_id": assignment["merchant_id"],
            "eta_min": round(float(assignment["total_eta_s"]) / 60.0, 1),
            "created_at_s": orders_by_id[assignment["order_id"]].created_at_s,
        }
        for assignment in challenger_assignments.values()
        if assignment["courier_id"] == courier.id and assignment["order_id"] in orders_by_id
    ]
    task_chain.sort(key=lambda item: (item["created_at_s"], item["order_id"]))
    latest_snapshot = _latest_courier_snapshot(courier.id, frames)
    assigned_count = len(task_chain)
    current_load = min(courier.capacity, assigned_count % (courier.capacity + 1))
    state = _rider_state(courier, latest_snapshot, assigned_count)
    return {
        "id": courier.id,
        "name": courier.label,
        "online_state": state,
        "shift_start_s": courier.shift_start_s,
        "shift_end_s": courier.shift_end_s,
        "shift_label": f"{_clock(courier.shift_start_s)}-{_clock(courier.shift_end_s)}",
        "business_area": courier.home_zone_id,
        "capacity": courier.capacity,
        "current_load": current_load,
        "task_chain": task_chain[:8],
        "task_chain_size": assigned_count,
        "estimated_free_at_s": int(latest_snapshot.get("available_at_s", courier.shift_start_s)) if latest_snapshot else courier.shift_start_s,
        "estimated_free_at_label": _clock(int(latest_snapshot.get("available_at_s", courier.shift_start_s))) if latest_snapshot else _clock(courier.shift_start_s),
        "performance": {
            "willingness": courier.willingness,
            "base_speed_mps": courier.base_speed_mps,
            "completed_orders": assigned_count,
            "summary": _rider_performance_summary(courier, assigned_count),
        },
        "position": _position_payload(latest_snapshot.get("position", courier.start_position) if latest_snapshot else courier.start_position),
        "mini_map": {
            "home": _position_payload(courier.start_position),
            "last": _position_payload(latest_snapshot.get("position", courier.start_position) if latest_snapshot else courier.start_position),
            "linked_order_ids": [item["order_id"] for item in task_chain[:4]],
        },
    }


def _decision_payload(
    frame: Any,
    trace: Any | None,
    time_slice: Any,
    orders_by_id: dict[str, Any],
    couriers_by_id: dict[str, Any],
    memory_by_id: dict[str, Any],
) -> dict[str, Any]:
    input_order_ids = list(frame.challenger.active_order_ids)
    candidate_courier_ids = sorted(
        {
            assignment.courier_id
            for assignment in (*frame.baseline.assignments, *frame.challenger.assignments)
        }
        | set(frame.highlighted_courier_ids)
    )
    final_actions = [
        {
            "order_id": assignment.order_id,
            "courier_id": assignment.courier_id,
            "merchant_id": assignment.merchant_id,
            "total_eta_min": round(assignment.total_eta_s / 60.0, 1),
            "expected_cost_yuan": assignment.expected_cost_yuan,
            "timeout_risk": assignment.timeout_risk,
        }
        for assignment in frame.challenger.assignments
    ]
    abandoned_actions = [
        {
            "order_id": assignment.order_id,
            "courier_id": assignment.courier_id,
            "reason": "Baseline nearest-only assignment was rejected by risk-balanced scoring.",
        }
        for assignment in frame.baseline.assignments
        if assignment.order_id in input_order_ids
        and not any(
            action["order_id"] == assignment.order_id and action["courier_id"] == assignment.courier_id
            for action in final_actions
        )
    ][:8]
    candidate_scores = []
    if trace is not None:
        candidate_scores = [
            {
                "algorithm_id": score.algorithm_id,
                "score": score.score,
                "estimated_runtime_ms": score.estimated_runtime_ms,
                "expected_time_cost_s": score.expected_time_cost_s,
                "expected_cost_yuan": score.expected_cost_yuan,
                "risk_score": score.risk_score,
                "reason": score.reason,
            }
            for score in trace.candidate_scores
        ]
    return {
        "id": f"D-{frame.id}",
        "frame_id": frame.id,
        "trigger_time_s": frame.sim_time_s,
        "trigger_time_label": _clock(frame.sim_time_s),
        "trigger_reason": _trigger_reason(time_slice),
        "input_order_ids": input_order_ids,
        "input_orders": [_order_reference(orders_by_id[order_id]) for order_id in input_order_ids if order_id in orders_by_id],
        "candidate_rider_ids": candidate_courier_ids,
        "candidate_riders": [_rider_reference(couriers_by_id[courier_id]) for courier_id in candidate_courier_ids if courier_id in couriers_by_id],
        "filtering_process": _filtering_process(time_slice, len(input_order_ids), len(candidate_courier_ids)),
        "scoring_process": candidate_scores,
        "final_actions": final_actions,
        "abandoned_actions": abandoned_actions,
        "round_result": {
            "summary": frame.challenger.decision_summary,
            "time_saved_min": round(frame.delta.time_saved_s / 60.0, 1),
            "cost_saved_yuan": frame.delta.cost_saved_yuan,
            "timeout_risk_delta": frame.delta.timeout_risk_delta,
            "extra_delivered_orders": frame.delta.extra_delivered_orders,
        },
        "result_writeback": {
            "memory_event_ids": list(frame.memory_event_ids),
            "writeback_count": sum(1 for event_id in frame.memory_event_ids if memory_by_id[event_id].writeback),
            "summary": "Decision outcome updates dispatch memory when the challenger improves cumulative cost or risk.",
        },
        "context": {
            "time_slice_id": time_slice.id,
            "demand_phase": time_slice.demand_phase,
            "weather": time_slice.weather,
            "congestion_level": time_slice.congestion_level,
            "courier_supply": time_slice.courier_supply,
            "shock_ids": list(time_slice.shock_ids),
        },
    }


def _memory_payload(event: Any, frame: Any, time_slice: Any, decision_id: str) -> dict[str, Any]:
    stage_by_type = {
        "memory_writeback": "new",
        "future_policy_shift": "curated",
        "memory_recall": "active",
    }
    stage = stage_by_type.get(event.event_type, "feedback")
    if event.event_type == "future_policy_shift" and event.confidence_after - event.confidence_before >= 0.04:
        effect_feedback = "Positive policy shift retained for similar contexts."
    elif event.event_type == "memory_recall":
        effect_feedback = "Historical context recalled before scoring candidates."
    else:
        effect_feedback = "Writeback confidence updated after round outcome."
    scope_by_type = {
        "memory_recall": "profile",
        "memory_writeback": "working",
        "future_policy_shift": "global",
    }
    channel_by_type = {
        "memory_recall": "recall-before-scoring",
        "memory_writeback": "decision-result-writeback",
        "future_policy_shift": "policy-curation",
    }
    return {
        "id": event.id,
        "stage": stage,
        "event_type": event.event_type,
        "memory_scope": scope_by_type.get(event.event_type, "working"),
        "formation_channel": channel_by_type.get(event.event_type, "feedback"),
        "trigger_scenario": event.context_signature,
        "context_summary": _memory_context_summary(time_slice),
        "strategy_summary": event.learned_rule,
        "decision_result": frame.delta.headline,
        "dispatch_effect": frame.delta.headline,
        "effect_feedback": effect_feedback,
        "confidence": event.confidence_after,
        "confidence_before": event.confidence_before,
        "confidence_after": event.confidence_after,
        "recall_count": len(event.recalled_case_ids),
        "recalled_case_ids": list(event.recalled_case_ids),
        "latest_hit_time_s": frame.sim_time_s,
        "latest_hit_time_label": _clock(frame.sim_time_s),
        "linked_decision_id": decision_id,
        "tags": [time_slice.demand_phase, time_slice.weather, *time_slice.shock_ids],
    }


def _memory_sections(memories: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        "new": [item["id"] for item in memories if item["stage"] == "new"],
        "curated": [item["id"] for item in memories if item["stage"] == "curated"],
        "active": [item["id"] for item in memories if item["stage"] == "active"],
        "feedback": [item["id"] for item in memories if item["event_type"] in {"memory_writeback", "future_policy_shift"}],
    }


def _memory_system(memories: list[dict[str, Any]]) -> dict[str, Any]:
    latest = _latest_memory_items(memories, limit=1)
    latest_item = latest[0] if latest else None
    return {
        "title": "Hermes Memory Command Center",
        "source_of_truth": "day-replay evolution events",
        "memory_count": len(memories),
        "avg_confidence": _avg_memory_confidence(memories),
        "recall_count": sum(int(item.get("recall_count", 0)) for item in memories),
        "linked_decision_count": len({item.get("linked_decision_id", "") for item in memories if item.get("linked_decision_id")}),
        "latest_hit_time_label": latest_item["latest_hit_time_label"] if latest_item else "-",
        "improvement_summary": latest_item["decision_result"] if latest_item else "No memory effect has been recorded yet.",
        "operating_model": "global policy + profile memories + active recall + writeback feedback",
    }


def _memory_layers(memories: list[dict[str, Any]], sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    item_by_id = {item["id"]: item for item in memories}
    active_ids = sections["active"]
    new_ids = sections["new"]
    curated_ids = sections["curated"]
    feedback_ids = sections["feedback"]
    return [
        _memory_layer_payload(
            layer_id="global-policy",
            label="全局策略记忆",
            scope="GLOBAL",
            item_ids=curated_ids,
            items=item_by_id,
            summary="跨时段保留的策略规则，用于在相似高峰、天气和供需结构中提前提高 AutoSolver 权重。",
            dispatch_use="进入 Planner 前作为全局先验，避免重新从最近距离基线开始试错。",
        ),
        _memory_layer_payload(
            layer_id="rider-profile",
            label="骑手画像记忆",
            scope="PROFILE",
            item_ids=active_ids,
            items=item_by_id,
            summary="沉淀骑手供给、负载和可用时间的历史画像，召回后参与候选骑手过滤。",
            dispatch_use="减少把近单派给即将满载或班次尾段骑手的概率。",
        ),
        _memory_layer_payload(
            layer_id="area-demand-profile",
            label="商圈/需求画像",
            scope="PROFILE",
            item_ids=new_ids,
            items=item_by_id,
            summary="把时段、天气、拥堵和商圈压力写成需求画像，供后续相似窗口复用。",
            dispatch_use="在订单进入前预判压力区，优先保护高风险承诺时效。",
        ),
        _memory_layer_payload(
            layer_id="order-risk-profile",
            label="订单风险画像",
            scope="PROFILE",
            item_ids=feedback_ids,
            items=item_by_id,
            summary="根据回写反馈提升或削弱风险规则置信度，保留对超时、空驶和成本有效的经验。",
            dispatch_use="评分时把超时风险和空驶代价并入同一策略记忆。",
        ),
    ]


def _memory_profiles(memories: list[dict[str, Any]], sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    item_by_id = {item["id"]: item for item in memories}
    return [
        _memory_profile_payload(
            profile_id="rider-supply",
            label="骑手供给画像",
            profile_type="rider",
            item_ids=sections["active"],
            items=item_by_id,
            context="供给稀缺、班次尾段、负载变化",
            strategy="候选骑手先按可用时间和后续连单能力过滤，再进入评分。",
        ),
        _memory_profile_payload(
            profile_id="area-pressure",
            label="商圈压力画像",
            profile_type="area",
            item_ids=sections["new"],
            items=item_by_id,
            context="午高峰、天气、拥堵、热点商圈订单密度",
            strategy="高压商圈保留更短承诺时间窗口，避免最近距离策略造成局部堵塞。",
        ),
        _memory_profile_payload(
            profile_id="order-risk",
            label="订单风险画像",
            profile_type="order",
            item_ids=sections["feedback"],
            items=item_by_id,
            context="高优先级订单、超时惩罚、空驶里程和成本回写",
            strategy="把风险收益比写入评分，使高风险单优先获得稳定骑手链路。",
        ),
    ]


def _memory_recall_chain(memories: list[dict[str, Any]], sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    item_by_id = {item["id"]: item for item in memories}
    active = _latest_ids(sections["active"], item_by_id, limit=1)
    recalled_item = item_by_id[active[0]] if active else None
    linked_decision_id = recalled_item.get("linked_decision_id", "") if recalled_item else ""
    decision_items = [
        item
        for item in memories
        if linked_decision_id and item.get("linked_decision_id") == linked_decision_id
    ]
    writeback_ids = [item["id"] for item in decision_items if item["stage"] == "new"]
    policy_ids = [item["id"] for item in decision_items if item["stage"] == "curated"]
    return [
        {
            "id": "hit",
            "label": "命中长期记忆",
            "item_ids": active,
            "summary": recalled_item["trigger_scenario"] if recalled_item else "No active recall yet.",
            "evidence": recalled_item["context_summary"] if recalled_item else "-",
        },
        {
            "id": "inject",
            "label": "注入候选评分",
            "item_ids": active,
            "summary": recalled_item["strategy_summary"] if recalled_item else "Recall waits for the first decision round.",
            "evidence": f"linked decision {linked_decision_id}" if linked_decision_id else "-",
        },
        {
            "id": "decide",
            "label": "影响最终动作",
            "item_ids": policy_ids or active,
            "summary": recalled_item["decision_result"] if recalled_item else "-",
            "evidence": "Scorecard keeps time/cost/timeout advantage against baseline.",
        },
        {
            "id": "writeback",
            "label": "结果回写记忆",
            "item_ids": writeback_ids or policy_ids,
            "summary": "Round outcome updates working memory and curated policy confidence.",
            "evidence": "Only positive or useful policy shifts are retained for later recall.",
        },
    ]


def _memory_writeback_loop(memories: list[dict[str, Any]], sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    item_by_id = {item["id"]: item for item in memories}
    return [
        {
            "id": "new-memory",
            "label": "新沉淀记忆",
            "item_ids": _latest_ids(sections["new"], item_by_id, limit=2),
            "summary": "每轮结果把有效策略、上下文和收益差异写成候选记忆。",
        },
        {
            "id": "curated-memory",
            "label": "已整理记忆",
            "item_ids": _latest_ids(sections["curated"], item_by_id, limit=2),
            "summary": "置信度提升后的规则进入全局策略记忆，供未来相似场景直接召回。",
        },
        {
            "id": "active-memory",
            "label": "当前命中的记忆",
            "item_ids": _latest_ids(sections["active"], item_by_id, limit=2),
            "summary": "当前窗口只展示与本轮推理相关的命中，不把历史日志全部铺开。",
        },
        {
            "id": "feedback-memory",
            "label": "记忆效果反馈",
            "item_ids": _latest_ids(sections["feedback"], item_by_id, limit=2),
            "summary": "用时间、成本、超时和空驶结果验证记忆是否继续保留。",
        },
    ]


def _memory_layer_payload(
    *,
    layer_id: str,
    label: str,
    scope: str,
    item_ids: list[str],
    items: dict[str, dict[str, Any]],
    summary: str,
    dispatch_use: str,
) -> dict[str, Any]:
    selected = [items[item_id] for item_id in _latest_ids(item_ids, items, limit=6)]
    return {
        "id": layer_id,
        "label": label,
        "scope": scope,
        "item_ids": [item["id"] for item in selected],
        "memory_count": len(item_ids),
        "avg_confidence": _avg_memory_confidence(selected),
        "recall_count": sum(int(item.get("recall_count", 0)) for item in selected),
        "latest_hit_time_label": selected[0]["latest_hit_time_label"] if selected else "-",
        "summary": summary,
        "dispatch_use": dispatch_use,
        "effect": selected[0]["decision_result"] if selected else "Waiting for replay evidence.",
    }


def _memory_profile_payload(
    *,
    profile_id: str,
    label: str,
    profile_type: str,
    item_ids: list[str],
    items: dict[str, dict[str, Any]],
    context: str,
    strategy: str,
) -> dict[str, Any]:
    selected = [items[item_id] for item_id in _latest_ids(item_ids, items, limit=3)]
    return {
        "id": profile_id,
        "label": label,
        "profile_type": profile_type,
        "item_ids": [item["id"] for item in selected],
        "context": context,
        "strategy": strategy,
        "confidence": _avg_memory_confidence(selected),
        "latest_hit_time_label": selected[0]["latest_hit_time_label"] if selected else "-",
        "dispatch_effect": selected[0]["decision_result"] if selected else "No dispatch effect recorded yet.",
    }


def _latest_ids(item_ids: list[str], items: dict[str, dict[str, Any]], limit: int) -> list[str]:
    return [
        item["id"]
        for item in sorted(
            (items[item_id] for item_id in item_ids if item_id in items),
            key=lambda item: (item.get("latest_hit_time_s", 0), item.get("id", "")),
            reverse=True,
        )[:limit]
    ]


def _latest_memory_items(memories: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return sorted(
        memories,
        key=lambda item: (item.get("latest_hit_time_s", 0), item.get("id", "")),
        reverse=True,
    )[:limit]


def _avg_memory_confidence(memories: list[dict[str, Any]]) -> float:
    if not memories:
        return 0.0
    return round(
        sum(float(item.get("confidence", item.get("confidence_after", 0))) for item in memories) / len(memories),
        3,
    )


def _merchant_payload(merchant: Any) -> dict[str, Any]:
    return {
        "id": merchant.id,
        "label": merchant.label,
        "business_area": merchant.zone_id,
        "category": merchant.category,
        "position": _position_payload(merchant.position),
        "peak_capacity": merchant.peak_capacity,
        "prep_time_min": round(merchant.prep_time_s / 60.0, 1),
    }


def _shock_payload(shock: Any) -> dict[str, Any]:
    return {
        "id": shock.id,
        "type": shock.shock_type,
        "start_s": shock.start_s,
        "end_s": shock.end_s,
        "time_label": f"{_clock(shock.start_s)}-{_clock(shock.end_s)}",
        "affected_areas": list(shock.affected_zone_ids),
        "severity": shock.severity,
        "summary": shock.summary,
    }


def _time_slice_payload(time_slice: Any) -> dict[str, Any]:
    return {
        "id": time_slice.id,
        "index": time_slice.index,
        "start_s": time_slice.start_s,
        "end_s": time_slice.end_s,
        "label": time_slice.label,
        "demand_phase": time_slice.demand_phase,
        "weather": time_slice.weather,
        "congestion_level": time_slice.congestion_level,
        "courier_supply": time_slice.courier_supply,
        "order_ids": list(time_slice.order_ids),
        "shock_ids": list(time_slice.shock_ids),
        "compare_due": time_slice.compare_due,
    }


def _scorecard_payload(frame: Any) -> dict[str, Any]:
    baseline = frame.baseline.metrics
    challenger = frame.challenger.metrics
    distance_saved_m = round(baseline.total_distance_m - challenger.total_distance_m, 3)
    revenue_delta_yuan = round(challenger.gross_revenue_yuan - baseline.gross_revenue_yuan, 3)
    profit_delta_yuan = round(revenue_delta_yuan + frame.delta.cost_saved_yuan, 3)
    return {
        "frame_id": frame.id,
        "time_s": frame.sim_time_s,
        "time_label": _clock(frame.sim_time_s),
        "baseline": _metrics_payload(baseline),
        "ours": _metrics_payload(challenger),
        "deltas": {
            "time_saved_s": frame.delta.time_saved_s,
            "time_saved_min": round(frame.delta.time_saved_s / 60.0, 1),
            "money_saved_yuan": frame.delta.cost_saved_yuan,
            "timeout_order_delta": challenger.late_orders - baseline.late_orders,
            "timeout_risk_delta": frame.delta.timeout_risk_delta,
            "empty_mileage_saved_m": distance_saved_m,
            "empty_mileage_saved_km": round(distance_saved_m / 1000.0, 2),
            "revenue_delta_yuan": revenue_delta_yuan,
            "profit_delta_yuan": profit_delta_yuan,
            "extra_delivered_orders": frame.delta.extra_delivered_orders,
            "utilization_delta": frame.delta.utilization_delta,
            "headline": frame.delta.headline,
        },
    }


def _metrics_payload(metrics: Any) -> dict[str, Any]:
    return {
        "total_orders": metrics.total_orders,
        "delivered_orders": metrics.delivered_orders,
        "assigned_orders": metrics.assigned_orders,
        "late_orders": metrics.late_orders,
        "coverage_rate": metrics.coverage_rate,
        "avg_eta_min": round(metrics.avg_eta_s / 60.0, 1),
        "p95_eta_min": round(metrics.p95_eta_s / 60.0, 1),
        "total_time_cost_min": round(metrics.total_time_cost_s / 60.0, 1),
        "total_distance_km": round(metrics.total_distance_m / 1000.0, 2),
        "total_cost_yuan": metrics.total_cost_yuan,
        "timeout_risk": metrics.timeout_risk,
        "courier_utilization": metrics.courier_utilization,
        "gross_revenue_yuan": metrics.gross_revenue_yuan,
    }


def _timeline_events(contract: DaySimulationContract, orders_by_id: dict[str, Any], memory_by_id: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for order in contract.orders:
        events.append(
            {
                "id": f"EV-order-{order.id}",
                "time_s": order.created_at_s,
                "time_label": _clock(order.created_at_s),
                "type": "order_entered",
                "order_id": order.id,
                "summary": f"Order {order.id} entered from merchant {order.merchant_id}.",
            }
        )
    for frame in contract.frames:
        events.append(
            {
                "id": f"EV-decision-{frame.id}",
                "time_s": frame.sim_time_s,
                "time_label": _clock(frame.sim_time_s),
                "type": "decision_round",
                "decision_id": f"D-{frame.id}",
                "order_ids": list(frame.challenger.active_order_ids),
                "courier_ids": list(frame.highlighted_courier_ids),
                "summary": frame.challenger.decision_summary,
            }
        )
        events.append(
            {
                "id": f"EV-score-{frame.id}",
                "time_s": frame.sim_time_s + 1,
                "time_label": _clock(frame.sim_time_s + 1),
                "type": "score_update",
                "frame_id": frame.id,
                "summary": frame.delta.headline,
            }
        )
        for event_id in frame.memory_event_ids:
            memory_event = memory_by_id[event_id]
            events.append(
                {
                    "id": f"EV-memory-{event_id}",
                    "time_s": frame.sim_time_s + 2,
                    "time_label": _clock(frame.sim_time_s + 2),
                    "type": memory_event.event_type,
                    "memory_id": event_id,
                    "summary": memory_event.learned_rule,
                }
            )
    events.sort(key=lambda item: (int(item["time_s"]), item["id"]))
    for index, event in enumerate(events):
        event["sequence"] = index + 1
        if event.get("order_id") in orders_by_id:
            event["business_area"] = orders_by_id[str(event["order_id"])].demand_phase
    return events


def _map_anchors(contract: DaySimulationContract) -> dict[str, list[dict[str, Any]]]:
    return {
        "merchants": [
            {
                "id": merchant.id,
                "label": merchant.label,
                "map_label": _map_alias("M", index),
                "area": merchant.zone_id,
                "position": _position_payload(merchant.position),
            }
            for index, merchant in enumerate(contract.merchants, start=1)
        ],
        "orders": [
            {
                "id": order.id,
                "map_label": _map_alias("O", index, width=3),
                "merchant_id": order.merchant_id,
                "created_at_s": order.created_at_s,
                "pickup": _position_payload(order.merchant_position),
                "dropoff": _position_payload(order.destination),
                "risk_level": _risk_level(order),
            }
            for index, order in enumerate(contract.orders, start=1)
        ],
        "riders": [
            {
                "id": courier.id,
                "label": courier.label,
                "map_label": _map_alias("R", index),
                "area": courier.home_zone_id,
                "position": _position_payload(courier.start_position),
            }
            for index, courier in enumerate(contract.couriers, start=1)
        ],
    }


def _map_aliases(contract: DaySimulationContract) -> dict[str, dict[str, str]]:
    return {
        "merchants": {merchant.id: _map_alias("M", index) for index, merchant in enumerate(contract.merchants, start=1)},
        "orders": {order.id: _map_alias("O", index, width=3) for index, order in enumerate(contract.orders, start=1)},
        "riders": {courier.id: _map_alias("R", index) for index, courier in enumerate(contract.couriers, start=1)},
    }


def _map_alias(prefix: str, index: int, *, width: int = 2) -> str:
    return f"{prefix}-{index:0{width}d}"


def _hotspots(contract: DaySimulationContract) -> list[dict[str, Any]]:
    zone_positions: dict[str, list[dict[str, float]]] = {}
    for merchant in contract.merchants:
        zone_positions.setdefault(merchant.zone_id, []).append(_position_payload(merchant.position))
    hotspots = []
    for shock in contract.shocks:
        points = [point for zone in shock.affected_zone_ids for point in zone_positions.get(zone, [])]
        if not points:
            continue
        hotspots.append(
            {
                "id": shock.id,
                "type": shock.shock_type,
                "start_s": shock.start_s,
                "end_s": shock.end_s,
                "severity": shock.severity,
                "summary": shock.summary,
                "center": _average_position(points),
                "affected_areas": list(shock.affected_zone_ids),
            }
        )
    return hotspots


def _route_payloads(contract: DaySimulationContract) -> list[dict[str, Any]]:
    routes = []
    for frame in contract.frames:
        for lane, algorithm_frame in (("baseline", frame.baseline), ("ours", frame.challenger)):
            for route in algorithm_frame.route_overlays:
                routes.append(
                    {
                        "id": f"ROUTE-{frame.id}-{lane}-{route.get('courier_id')}-{route.get('order_id')}",
                        "frame_id": frame.id,
                        "time_s": frame.sim_time_s,
                        "lane": lane,
                        "order_id": route.get("order_id", ""),
                        "courier_id": route.get("courier_id", ""),
                        "polyline": [_position_payload(point) for point in route.get("polyline", [])],
                        "eta_s": route.get("eta_s", 0),
                        "cost_yuan": route.get("cost_yuan", 0),
                    }
                )
    return routes


def _frame_by_order_id(contract: DaySimulationContract) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for frame in contract.frames:
        for order_id in frame.challenger.active_order_ids:
            result.setdefault(order_id, frame)
    return result


def _assignment_lookup(contract: DaySimulationContract, lane: str) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for frame in contract.frames:
        algorithm_frame = frame.baseline if lane == "baseline" else frame.challenger
        for assignment in algorithm_frame.assignments:
            lookup[assignment.order_id] = {
                "algorithm_id": algorithm_frame.algorithm_id,
                "order_id": assignment.order_id,
                "courier_id": assignment.courier_id,
                "merchant_id": assignment.merchant_id,
                "pickup_eta_s": assignment.pickup_eta_s,
                "delivery_eta_s": assignment.delivery_eta_s,
                "total_eta_s": assignment.total_eta_s,
                "expected_cost_yuan": assignment.expected_cost_yuan,
                "timeout_risk": assignment.timeout_risk,
                "rationale": assignment.rationale,
            }
    return lookup


def _algorithm_result_payload(assignment: dict[str, Any] | None, fallback_algorithm: str) -> dict[str, Any]:
    if assignment is None:
        return {
            "algorithm_id": fallback_algorithm,
            "state": "not_released",
            "courier_id": "",
            "eta_min": None,
            "expected_cost_yuan": None,
            "timeout_risk": None,
            "summary": "Not released into the emitted inference timeline yet.",
        }
    return {
        "algorithm_id": assignment["algorithm_id"],
        "state": "assigned",
        "courier_id": assignment["courier_id"],
        "eta_min": round(float(assignment["total_eta_s"]) / 60.0, 1),
        "expected_cost_yuan": assignment["expected_cost_yuan"],
        "timeout_risk": assignment["timeout_risk"],
        "summary": assignment["rationale"],
    }


def _latest_courier_snapshot(courier_id: str, frames: tuple[Any, ...]) -> dict[str, Any] | None:
    latest = None
    for frame in frames:
        for snapshot in frame.challenger.courier_positions:
            if snapshot.get("courier_id") == courier_id:
                latest = snapshot
    return latest


def _rider_state(courier: Any, latest_snapshot: dict[str, Any] | None, assigned_count: int) -> str:
    if assigned_count <= 0:
        return "available"
    if latest_snapshot and latest_snapshot.get("status") == "busy":
        return "busy"
    if courier.shift_end_s <= 22 * 60 * 60 and assigned_count > 0:
        return "ending_shift"
    return "available"


def _rider_performance_summary(courier: Any, assigned_count: int) -> str:
    if assigned_count >= 10 and courier.willingness >= 0.72:
        return "High-throughput rider with stable willingness during peaks."
    if assigned_count >= 4:
        return "Balanced rider used across multiple dispatch rounds."
    return "Reserve capacity for local-area pressure relief."


def _trigger_reason(time_slice: Any) -> str:
    if time_slice.shock_ids:
        return f"Pressure change: {', '.join(time_slice.shock_ids)}."
    if time_slice.compare_due:
        return "Planner comparison due under current order pressure."
    return f"Scheduled {time_slice.demand_phase} dispatch round."


def _filtering_process(time_slice: Any, order_count: int, rider_count: int) -> list[dict[str, Any]]:
    return [
        {
            "stage": "time_window",
            "summary": f"Release {order_count} orders in {time_slice.label}.",
            "remaining": order_count,
        },
        {
            "stage": "area_and_shift",
            "summary": f"Keep riders online for affected areas and current shifts.",
            "remaining": rider_count,
        },
        {
            "stage": "risk_guardrail",
            "summary": f"Apply weather, congestion and deadline guardrails at {time_slice.congestion_level:.2f} congestion.",
            "remaining": max(1, min(order_count, rider_count)),
        },
    ]


def _order_reference(order: Any) -> dict[str, Any]:
    return {
        "id": order.id,
        "merchant_id": order.merchant_id,
        "created_at_s": order.created_at_s,
        "deadline_s": order.deadline_s,
        "risk_level": _risk_level(order),
    }


def _rider_reference(courier: Any) -> dict[str, Any]:
    return {
        "id": courier.id,
        "name": courier.label,
        "area": courier.home_zone_id,
        "capacity": courier.capacity,
        "willingness": courier.willingness,
    }


def _memory_context_summary(time_slice: Any) -> str:
    pressure = "shock pressure" if time_slice.shock_ids else "steady pressure"
    return (
        f"{time_slice.demand_phase} / {time_slice.weather} / congestion {time_slice.congestion_level:.2f} "
        f"with {time_slice.courier_supply} riders under {pressure}."
    )


def _order_time_bands(contract: DaySimulationContract) -> list[dict[str, Any]]:
    phases: dict[str, list[int]] = {}
    for time_slice in contract.time_slices:
        phases.setdefault(time_slice.demand_phase, []).extend([time_slice.start_s, time_slice.end_s])
    return [
        {
            "id": phase,
            "label": phase.replace("_", " ").title(),
            "start_s": min(values),
            "end_s": max(values),
            "time_label": f"{_clock(min(values))}-{_clock(max(values))}",
        }
        for phase, values in sorted(phases.items(), key=lambda item: min(item[1]))
    ]


def _risk_level(order: Any) -> str:
    if order.priority >= 0.74 or len(order.risk_tags) >= 3:
        return "high"
    if order.priority >= 0.48 or order.risk_tags:
        return "medium"
    return "low"


def _position_payload(position: Any) -> dict[str, float]:
    if isinstance(position, dict):
        return {
            "lat": round(float(position["lat"]), 6),
            "lng": round(float(position["lng"]), 6),
            "screen_x": round(float(position.get("screen_x", 50.0)), 2),
            "screen_y": round(float(position.get("screen_y", 50.0)), 2),
        }
    return {
        "lat": round(float(position.lat), 6),
        "lng": round(float(position.lng), 6),
        "screen_x": round(float(position.screen_x), 2),
        "screen_y": round(float(position.screen_y), 2),
    }


def _average_position(points: list[dict[str, float]]) -> dict[str, float]:
    return {
        "lat": round(sum(point["lat"] for point in points) / len(points), 6),
        "lng": round(sum(point["lng"] for point in points) / len(points), 6),
        "screen_x": round(sum(point["screen_x"] for point in points) / len(points), 2),
        "screen_y": round(sum(point["screen_y"] for point in points) / len(points), 2),
    }


def _clock(seconds: int | float) -> str:
    seconds_int = int(seconds)
    hours = seconds_int // 3600
    minutes = (seconds_int % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"
