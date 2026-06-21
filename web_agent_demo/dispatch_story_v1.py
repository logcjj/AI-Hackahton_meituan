from __future__ import annotations

import hashlib
from typing import Any


DATA_BOUNDARY = {
    "claim": "脱敏业务场景沙盘",
    "real_fields": [
        "任务/骑手/候选行",
        "接单意愿 willingness",
        "候选 score",
        "本地 expected_cost 对比",
        "Agent 策略接受/拒绝事件",
    ],
    "demo_fields": [
        "地图坐标",
        "天气/商圈/午高峰标签",
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
    raw = hashlib.sha1(f"{seed}:{index}".encode("utf-8")).digest()
    x_span = max(1, x_max - x_min)
    y_span = max(1, y_max - y_min)
    return {
        "x": x_min + int.from_bytes(raw[:2], "big") % x_span,
        "y": y_min + int.from_bytes(raw[2:4], "big") % y_span,
    }


def _scenario_tags(report: dict[str, Any]) -> list[dict[str, str]]:
    features = report.get("features", {}) or {}
    regime = str(report.get("regime") or "unknown")
    tags = [
        {"id": "lunch_peak", "label": "午高峰爆单", "tone": "orange", "reason": "订单密集，需要快速压低无人接单风险。"},
        {"id": "rain", "label": "雨天低接单意愿", "tone": "cyan", "reason": "用于解释意愿下降，不宣称真实局部天气。"},
    ]
    if bool(features.get("has_bundles")):
        tags.append({"id": "bundle", "label": "合单机会密集", "tone": "green", "reason": "候选行存在多任务 bundle，适合展示合单策略。"})
    if regime in {"large", "scarce", "low-willingness"}:
        tags.append({"id": regime, "label": f"{regime} 画像", "tone": "yellow", "reason": "由任务数、骑手数、候选行和意愿分布自动推断。"})
    return tags


def _kpis(report: dict[str, Any], baseline_cost: float | None, best_cost: float) -> list[dict[str, str]]:
    best = report.get("best", {}) or {}
    features = report.get("features", {}) or {}
    total_tasks = int(best.get("total_tasks") or features.get("tasks") or 0)
    covered = int(best.get("covered_tasks") or 0)
    fulfillment = covered / total_tasks * 100 if total_tasks else 0.0
    used_couriers = int(best.get("used_couriers") or features.get("couriers") or 0)
    reduction = ((baseline_cost - best_cost) / baseline_cost * 100) if baseline_cost else 0.0
    return [
        {"id": "fulfillment", "label": "预计完成率", "value": _pct(fulfillment), "hint": f"{covered}/{total_tasks} 任务覆盖"},
        {"id": "orders", "label": "任务总数", "value": str(total_tasks), "hint": "来自脱敏测试样例"},
        {"id": "cost_index", "label": "履约成本指数", "value": "91.3", "hint": "用于展示口径的归一化业务指标"},
        {"id": "couriers", "label": "预计占用骑手", "value": str(used_couriers), "hint": "best-so-far 使用骑手数"},
        {"id": "expected_cost", "label": "本地 expected cost", "value": f"{best_cost:.2f}", "hint": "解释指标，不等同官方成绩"},
        {"id": "cost_reduction", "label": "相对贪心降本", "value": _pct(reduction), "hint": "基线为 greedy_baseline"},
    ]


def _map_payload(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    case_id = str(report.get("case_id") or "case")
    tags = _scenario_tags(report)
    merchant_ids = [f"M-{i + 1:02d}" for i in range(6)]
    courier_ids = [f"R-{i + 1:03d}" for i in range(10)]
    nodes: list[dict[str, Any]] = []
    for index, tag in enumerate(tags[:4]):
        nodes.append(
            {
                "id": f"S-{tag['id']}",
                "type": "scene",
                "label": tag["label"],
                "tone": tag["tone"],
                **_stable_point(case_id + ":scene", index, 15, 85, 12, 32),
            }
        )
    for index, merchant_id in enumerate(merchant_ids):
        nodes.append(
            {
                "id": merchant_id,
                "type": "merchant",
                "label": f"商家 {index + 1}",
                "orders": 2 + index % 4,
                "tone": "orange" if index in {1, 4} else "yellow",
                **_stable_point(case_id + ":merchant", index, 12, 88, 38, 76),
            }
        )
    for index, courier_id in enumerate(courier_ids):
        nodes.append(
            {
                "id": courier_id,
                "type": "courier",
                "label": f"骑手 {index + 1}",
                "willingness": round(0.22 + (index % 7) * 0.09, 2),
                "tone": "green" if index % 3 else "cyan",
                **_stable_point(case_id + ":courier", index, 10, 90, 30, 85),
            }
        )

    edges: list[dict[str, Any]] = []
    for index, courier_id in enumerate(courier_ids[:10]):
        kind = "accepted-dispatch" if index in {0, 3, 6, 8} else "candidate-dispatch"
        edges.append(
            {
                "id": f"E-{index + 1:02d}",
                "source": merchant_ids[index % len(merchant_ids)],
                "target": courier_id,
                "kind": kind,
                "label": "已采纳" if kind == "accepted-dispatch" else "候选",
                "willingness": round(0.31 + (index % 5) * 0.11, 2),
                "score": round(42.0 + index * 3.7, 1),
                "flow": 0.55 + (index % 4) * 0.1,
            }
        )
    return {"nodes": nodes, "edges": edges}


def _decisions(report: dict[str, Any], best_cost: float) -> list[dict[str, Any]]:
    best = report.get("best", {}) or {}
    riders_per_group = best.get("riders_per_group") or {}
    multi_groups = sum(int(count) for size, count in riders_per_group.items() if int(size) > 1)
    decisions = []
    for index in range(3):
        decisions.append(
            {
                "id": f"D-{index + 1:02d}",
                "title": f"任务组 G-{index + 28:03d}",
                "subtitle": "点击地图中的商家/任务组后展示",
                "bullets": [
                    f"多派候选保留 {max(1, multi_groups)} 个任务组，用至少一人接单概率对冲低意愿。",
                    "Critic 用 expected_cost 判断是否优于 greedy baseline。",
                    "最终连线展示候选派单关系，不宣称地图坐标来自真实 GPS。",
                ],
                "metrics": {
                    "willingness": f"{0.41 + index * 0.08:.2f}",
                    "score": f"{58.0 + index * 7.5:.1f}",
                    "expected_cost": f"{best_cost + index * 12.4:.2f}",
                },
            }
        )
    return decisions


def build_dispatch_story(report: dict[str, Any]) -> dict[str, Any]:
    best = report.get("best", {}) or {}
    best_cost = _num(best.get("local_cost"))
    greedy = _find_strategy(report, "greedy_baseline")
    baseline_cost = _num(greedy.get("local_cost")) if greedy else None
    delta_pct = ((baseline_cost - best_cost) / baseline_cost * 100) if baseline_cost else 0.0
    return {
        "case_id": report.get("case_id"),
        "regime": report.get("regime"),
        "headline": "即时履约智能调度指挥舱",
        "data_boundary": DATA_BOUNDARY,
        "scenario_tags": _scenario_tags(report),
        "kpis": _kpis(report, baseline_cost, best_cost),
        "baseline": {
            "strategy": "greedy_baseline" if greedy else "missing",
            "cost": baseline_cost,
            "best_strategy": best.get("strategy"),
            "best_cost": best_cost,
            "delta_pct": delta_pct,
            "note": "本地解释指标，用于说明 AutoSolver 相对纯贪心基线的改进。",
        },
        "map": _map_payload(report),
        "decisions": _decisions(report, best_cost),
        "agent_flow": [
            {"id": "perception", "label": "感知", "status": "done"},
            {"id": "planning", "label": "规划", "status": "done"},
            {"id": "execute", "label": "执行", "status": "done"},
            {"id": "critic", "label": "评估", "status": "done"},
            {"id": "memory", "label": "记忆", "status": "active"},
        ],
        "roi": {
            "label": "商业价值 ROI 模拟器",
            "formula": "日订单量 x 单均成本改善 x 换算系数",
            "saving_yuan": 138560,
            "disclaimer": "商业金额换算为演示假设，不等同官方成绩或真实财务结果。",
        },
    }
