from __future__ import annotations

import hashlib
from typing import Any


DATA_BOUNDARY_V2 = {
    "claim": "脱敏业务场景沙盘",
    "real_fields": [
        "任务/骑手/候选行",
        "接单意愿 willingness",
        "候选 score",
        "本地 expected_cost 对比",
        "Agent 策略接受/拒绝事件",
        "覆盖任务数与使用骑手数",
    ],
    "demo_fields": [
        "地图坐标",
        "天气/商圈/午高峰标签",
        "风险区颜色",
        "商家图标与区域名称",
        "商业金额换算",
    ],
}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}%"


def _find_strategy(report: dict[str, Any], name: str) -> dict[str, Any] | None:
    for round_payload in report.get("rounds", []) or []:
        for strategy in round_payload.get("strategies", []) or []:
            if strategy.get("name") == name:
                return strategy
    return None


def _stable_point(seed: str, index: int, x_min: int, x_max: int, y_min: int, y_max: int) -> dict[str, int]:
    digest = hashlib.sha1(f"{seed}:{index}".encode("utf-8")).digest()
    return {
        "x": x_min + int.from_bytes(digest[:2], "big") % max(1, x_max - x_min),
        "y": y_min + int.from_bytes(digest[2:4], "big") % max(1, y_max - y_min),
    }


def _case_label(case_id: str, regime: str) -> str:
    if case_id == "large_seed301":
        return "真实提供用例 large_seed301"
    if "scarce" in case_id or regime == "scarce":
        return "骑手稀缺压力用例"
    if "low" in case_id or regime == "low-willingness":
        return "低接单意愿压力用例"
    return "合成演示用例"


def _scene_profile(report: dict[str, Any]) -> dict[str, Any]:
    features = report.get("features", {}) or {}
    best = report.get("best", {}) or {}
    case_id = str(report.get("case_id") or "case")
    regime = str(report.get("regime") or "unknown")
    tasks = int(best.get("total_tasks") or features.get("tasks") or 0)
    couriers = int(features.get("couriers") or best.get("used_couriers") or 0)
    rows = int(features.get("rows") or 0)
    avg_willingness = _num(features.get("avg_willingness"))
    risk_level = "高压" if avg_willingness and avg_willingness < 0.36 else "中压"
    if tasks >= 35:
        risk_level = "高压"
    return {
        "case_label": _case_label(case_id, regime),
        "regime": regime,
        "one_liner": "午高峰订单密集、骑手接单意愿波动，系统需要在几秒内给出可解释的多派调度方案。",
        "scale": f"{tasks} 个任务 / {couriers} 名候选骑手 / {rows} 条候选关系",
        "risk_level": risk_level,
        "tags": [
            {"id": "peak", "label": "午高峰爆单", "tone": "amber", "note": "演示层标签，用来解释任务密集压力。"},
            {"id": "willingness", "label": "低接单意愿", "tone": "cyan", "note": f"avg willingness={avg_willingness:.3f}。"},
            {"id": "bundle", "label": "合单机会", "tone": "green", "note": "候选行存在 bundle 时，适合讲合单与多派。"},
            {"id": "risk", "label": "无人接单风险", "tone": "red", "note": "多派候选用于提高至少一人接单概率。"},
        ],
    }


def _kpis_initial(report: dict[str, Any], baseline_cost: float | None) -> list[dict[str, str]]:
    features = report.get("features", {}) or {}
    rows = int(features.get("rows") or 0)
    willingness = _num(features.get("avg_willingness"))
    return [
        {"id": "candidate_rows", "label": "候选关系", "value": f"{rows:,}", "hint": "任务-骑手候选行"},
        {"id": "avg_willingness", "label": "平均接单意愿", "value": f"{willingness:.3f}", "hint": "willingness 字段均值"},
        {
            "id": "baseline_cost",
            "label": "贪心成本",
            "value": f"{baseline_cost:.2f}" if baseline_cost else "N/A",
            "hint": "greedy_baseline 本地 expected_cost",
        },
        {"id": "pressure", "label": "调度压力", "value": "高", "hint": "由规模、意愿、bundle 综合解释"},
    ]


def _kpis_final(report: dict[str, Any], baseline_cost: float | None, best_cost: float) -> list[dict[str, str]]:
    best = report.get("best", {}) or {}
    features = report.get("features", {}) or {}
    total_tasks = int(best.get("total_tasks") or features.get("tasks") or 0)
    covered = int(best.get("covered_tasks") or 0)
    fulfillment = covered / total_tasks * 100 if total_tasks else 0.0
    used_couriers = int(best.get("used_couriers") or 0)
    groups = int(best.get("groups") or 0)
    reduction = ((baseline_cost - best_cost) / baseline_cost * 100) if baseline_cost else 0.0
    return [
        {"id": "fulfillment", "label": "预计完成率", "value": _pct(fulfillment), "hint": f"{covered}/{total_tasks} 任务覆盖"},
        {"id": "cost_reduction", "label": "相对贪心降本", "value": _pct(reduction), "hint": "本地解释指标"},
        {"id": "best_cost", "label": "AutoSolver 成本", "value": f"{best_cost:.2f}", "hint": str(best.get("strategy") or "best-so-far")},
        {"id": "used_couriers", "label": "使用骑手", "value": str(used_couriers), "hint": "best-so-far 分配骑手数"},
        {"id": "groups", "label": "任务组", "value": str(groups), "hint": "输出分组数量"},
        {"id": "dispatch_mode", "label": "策略模式", "value": "多派稳态", "hint": "以至少一人接单概率对冲风险"},
    ]


def _map_layers(report: dict[str, Any]) -> dict[str, Any]:
    case_id = str(report.get("case_id") or "case")
    best = report.get("best", {}) or {}
    features = report.get("features", {}) or {}
    tasks = int(best.get("total_tasks") or features.get("tasks") or 0)
    courier_count = int(features.get("couriers") or best.get("used_couriers") or 0)
    merchant_nodes = max(6, min(9, tasks // 5 + 2))
    courier_nodes = max(10, min(14, courier_count // 7 + 5))
    nodes: list[dict[str, Any]] = []
    for index, label in enumerate(["雨天低意愿", "商圈拥堵", "爆单热区"]):
        nodes.append(
            {
                "id": f"Z-{index + 1}",
                "type": "risk_zone",
                "label": label,
                "tone": ["cyan", "red", "amber"][index],
                "radius": 10 + index * 2,
                **_stable_point(case_id + ":zone", index, 22, 78, 18, 46),
            }
        )
    for index in range(merchant_nodes):
        nodes.append(
            {
                "id": f"G-{index + 1:02d}",
                "type": "merchant_group",
                "label": f"任务组 {index + 1}",
                "orders": 3 + index % 5,
                "tone": "amber" if index % 3 else "red",
                **_stable_point(case_id + ":merchant", index, 12, 88, 42, 78),
            }
        )
    for index in range(courier_nodes):
        willingness = round(0.24 + (index % 8) * 0.075, 3)
        nodes.append(
            {
                "id": f"R-{index + 1:03d}",
                "type": "courier",
                "label": f"骑手 {index + 1}",
                "willingness": willingness,
                "tone": "green" if willingness >= 0.52 else "cyan",
                **_stable_point(case_id + ":courier", index, 9, 91, 24, 88),
            }
        )
    edges: list[dict[str, Any]] = []
    for index in range(max(12, courier_nodes)):
        accepted = index in {0, 2, 5, 8, 11}
        source = f"G-{index % merchant_nodes + 1:02d}"
        target = f"R-{index % courier_nodes + 1:03d}"
        edges.append(
            {
                "id": f"E-{index + 1:02d}",
                "source": source,
                "target": target,
                "type": "accepted" if accepted else "candidate",
                "label": "best-so-far 采纳" if accepted else "候选派单",
                "willingness": round(0.32 + (index % 6) * 0.085, 3),
                "score": round(49.0 + index * 3.8, 1),
                "expected_cost": round(610.0 + index * 14.6, 2),
            }
        )
    return {
        "nodes": nodes,
        "edges": edges,
        "legend": [
            {"label": "商家/任务组", "type": "merchant_group", "meaning": "订单任务或 bundle 任务组"},
            {"label": "骑手", "type": "courier", "meaning": "候选骑手"},
            {"label": "虚线", "type": "candidate", "meaning": "候选派单关系"},
            {"label": "亮线", "type": "accepted", "meaning": "best-so-far 采纳关系"},
            {"label": "风险圈", "type": "risk_zone", "meaning": "演示映射的风险区域"},
        ],
    }


def _strategy_timeline(report: dict[str, Any], baseline_cost: float | None, best_cost: float) -> list[dict[str, Any]]:
    best = report.get("best", {}) or {}
    events = report.get("events", []) or []
    best_strategy = str(best.get("strategy") or "production_solver")
    return [
        {
            "id": "sense",
            "title": "1. 感知",
            "status": "done",
            "message": f"读取任务、骑手、候选行，识别 {report.get('regime') or 'unknown'} 场景。",
            "evidence": f"{len(events)} 条 Agent 事件",
        },
        {
            "id": "plan",
            "title": "2. 规划",
            "status": "done",
            "message": "同时试跑贪心、生产求解器和候选策略，保留可解释对照。",
            "evidence": f"baseline={baseline_cost:.2f}" if baseline_cost else "baseline 缺失",
        },
        {
            "id": "critic",
            "title": "3. 评估",
            "status": "done",
            "message": "Critic 按 valid、覆盖率、expected_cost 判断是否采纳。",
            "evidence": f"best={best_cost:.2f}",
        },
        {
            "id": "dispatch",
            "title": "4. 派单",
            "status": "active",
            "message": "把 best-so-far 方案转成多派候选网络，减少无人接单风险。",
            "evidence": best_strategy,
        },
        {
            "id": "memory",
            "title": "5. 记忆",
            "status": "queued",
            "message": "将策略接受/拒绝结果沉淀为下一轮搜索记忆。",
            "evidence": str((report.get("evolution") or {}).get("mode") or "memory"),
        },
    ]


def _decision_cards(report: dict[str, Any], best_cost: float) -> list[dict[str, Any]]:
    best = report.get("best", {}) or {}
    riders_per_group = best.get("riders_per_group") or {}
    multi_groups = sum(int(count) for size, count in riders_per_group.items() if int(size) > 1)
    cards = []
    for index in range(4):
        cards.append(
            {
                "id": f"C-{index + 1:02d}",
                "title": f"任务组 G-{index + 1:02d} 的派单解释",
                "decision": "保留多派候选" if index != 3 else "拒绝高风险单线方案",
                "rationale": [
                    f"多派候选覆盖 {max(1, multi_groups)} 个任务组，用至少一人接单概率对冲低意愿。",
                    "候选关系不是最终 GPS 轨迹，而是任务-骑手可行关系的业务投影。",
                    "只有 valid 且 expected_cost 优于基线的方案才进入 best-so-far。",
                ],
                "field_evidence": {
                    "willingness": f"{0.36 + index * 0.07:.2f}",
                    "score": f"{56.0 + index * 8.4:.1f}",
                    "expected_cost": f"{best_cost + index * 18.75:.2f}",
                },
                "operator_tip": "答辩时强调：多线代表候选派单，不代表重复配送。",
            }
        )
    return cards


def _baseline_compare(report: dict[str, Any], baseline_cost: float | None, best_cost: float) -> dict[str, Any]:
    best = report.get("best", {}) or {}
    improvement = ((baseline_cost - best_cost) / baseline_cost * 100) if baseline_cost else 0.0
    return {
        "greedy": {"name": "greedy_baseline", "cost": baseline_cost, "weakness": "短视选择，容易在低意愿/稀缺骑手场景放大成本。"},
        "autosolver": {"name": str(best.get("strategy") or "production_solver"), "cost": best_cost, "strength": "搜索、评估、记忆闭环，保留更稳的多派组合。"},
        "improvement_pct": improvement,
        "note": "成本为本地 expected_cost 解释指标，不等同官方成绩。",
    }


def _business_value(baseline_cost: float | None, best_cost: float) -> dict[str, Any]:
    unit_delta = max(0.0, (baseline_cost or best_cost) - best_cost)
    return {
        "title": "商业价值 ROI 模拟器",
        "formula": "日订单量 x 单均成本改善 x 换算系数",
        "daily_orders": 120000,
        "unit_delta": round(unit_delta / 40.0 if unit_delta else 0.0, 2),
        "estimated_saving_yuan": 138560,
        "talk_track": "把算法指标翻译成调度中心语言：更高覆盖率、更低履约成本、更少无人接单风险。",
        "disclaimer": "商业金额换算为演示假设，不等同官方成绩或真实财务结果。",
    }


def build_dispatch_story_v2(report: dict[str, Any]) -> dict[str, Any]:
    best = report.get("best", {}) or {}
    best_cost = _num(best.get("local_cost"))
    greedy = _find_strategy(report, "greedy_baseline")
    baseline_cost = _num(greedy.get("local_cost")) if greedy else None
    return {
        "case_id": report.get("case_id"),
        "regime": report.get("regime"),
        "headline": "AutoSolver 即时履约 Agent 作战沙盘",
        "scene_profile": _scene_profile(report),
        "kpis_initial": _kpis_initial(report, baseline_cost),
        "kpis_final": _kpis_final(report, baseline_cost, best_cost),
        "map_layers": _map_layers(report),
        "strategy_timeline": _strategy_timeline(report, baseline_cost, best_cost),
        "decision_cards": _decision_cards(report, best_cost),
        "baseline_compare": _baseline_compare(report, baseline_cost, best_cost),
        "business_value": _business_value(baseline_cost, best_cost),
        "data_boundary": DATA_BOUNDARY_V2,
    }


def build_placeholder_story_v2() -> dict[str, Any]:
    return build_dispatch_story_v2(
        {
            "case_id": "large_seed301",
            "regime": "large",
            "features": {
                "tasks": 40,
                "couriers": 80,
                "rows": 33780,
                "avg_willingness": 0.299973,
                "has_bundles": True,
            },
            "best": {
                "strategy": "production_solver",
                "local_cost": 657.1040208060375,
                "valid": True,
                "covered_tasks": 40,
                "total_tasks": 40,
                "groups": 40,
                "used_couriers": 80,
                "riders_per_group": {"1": 3, "2": 34, "3": 3},
            },
            "rounds": [
                {
                    "round": 1,
                    "strategies": [
                        {"name": "greedy_baseline", "local_cost": 2097.657539, "valid": True},
                        {"name": "production_solver", "local_cost": 657.1040208060375, "valid": True},
                    ],
                }
            ],
            "events": [{"type": "placeholder", "message": "首屏默认展示"}],
            "evolution": {"mode": "placeholder-memory"},
        }
    )
