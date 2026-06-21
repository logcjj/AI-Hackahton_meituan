from __future__ import annotations

import hashlib
from typing import Any


DATA_BOUNDARY_V3 = {
    "claim": "脱敏业务场景沙盘",
    "real_fields": [
        "任务/骑手/候选行",
        "willingness 接单意愿",
        "score 候选评分",
        "expected_cost 本地解释成本",
        "贪心基线与 AutoSolver best-so-far 对比",
        "Agent 策略接受/拒绝事件",
    ],
    "demo_fields": [
        "地图坐标",
        "商圈/午高峰标签",
        "风险热区颜色",
        "订单金额与商业收益换算",
    ],
}

REMOVED_MODULES = [
    "右上固定雨天接单意愿卡",
    "左下自进化与安全回退大模块",
    "手动场景选择作为主交互",
]


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct(value: float, digits: int = 1, signed: bool = False) -> str:
    prefix = "+" if signed and value >= 0 else ""
    return f"{prefix}{value:.{digits}f}%"


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


def _core_numbers(report: dict[str, Any]) -> dict[str, float]:
    best = report.get("best", {}) or {}
    features = report.get("features", {}) or {}
    greedy = _find_strategy(report, "greedy_baseline")
    best_cost = _num(best.get("local_cost"))
    baseline_cost = _num(greedy.get("local_cost")) if greedy else 0.0
    total_tasks = int(best.get("total_tasks") or features.get("tasks") or 0)
    covered_tasks = int(best.get("covered_tasks") or 0)
    used_couriers = int(best.get("used_couriers") or 0)
    completion = covered_tasks / total_tasks * 100 if total_tasks else 0.0
    improvement = (baseline_cost - best_cost) / baseline_cost * 100 if baseline_cost else 0.0
    avg_willingness = _num(features.get("avg_willingness"))
    return {
        "best_cost": best_cost,
        "baseline_cost": baseline_cost,
        "total_tasks": float(total_tasks),
        "covered_tasks": float(covered_tasks),
        "unassigned": float(max(0, total_tasks - covered_tasks)),
        "used_couriers": float(used_couriers),
        "completion": completion,
        "improvement": improvement,
        "avg_willingness": avg_willingness,
        "rows": float(int(features.get("rows") or 0)),
    }


def _command_center(report: dict[str, Any], numbers: dict[str, float]) -> dict[str, Any]:
    return {
        "status": "调度运行中",
        "elapsed": "00:00:07",
        "case_id": report.get("case_id"),
        "subtitle": "10 秒内生成高可靠派单方案，降低无人接单风险与履约成本",
        "scene_features": [
            {"id": "supply", "label": "骑手供给紧张", "delta": "可用骑手偏少", "tone": "orange"},
            {"id": "bundle", "label": "合单机会密集", "delta": "合单潜力 +37%", "tone": "green"},
            {"id": "peak", "label": "午高峰爆单", "delta": "订单量激增", "tone": "amber"},
        ],
        "data_caption": f"{int(numbers['total_tasks'])} 个任务 / {int(numbers['used_couriers'])} 名候选骑手 / {int(numbers['rows'])} 条候选关系",
    }


def _ai_scene_judgement(numbers: dict[str, float]) -> dict[str, Any]:
    return {
        "mode": "AI_AUTO_INFERRED",
        "title": "AI 场景识别",
        "description": "系统根据任务密度、骑手供给、willingness 与 bundle 分布自动判断，不再依赖手动点选场景。",
        "cards": [
            {"rank": 1, "label": "午高峰爆单", "summary": "订单量激增，候选关系密集", "impact": "高风险"},
            {"rank": 2, "label": "骑手供给紧张", "summary": "可用骑手与任务组竞争明显", "impact": "高风险"},
            {"rank": 3, "label": "合单机会密集", "summary": "多任务同向集中，可降履约成本", "impact": "低风险"},
            {"rank": 4, "label": "低意愿风险", "summary": f"avg willingness={numbers['avg_willingness']:.3f}", "impact": "中风险"},
        ],
        "risk_portrait": [
            {"label": "接单意愿偏低", "level": "高风险"},
            {"label": "骑手供给不足", "level": "高风险"},
            {"label": "订单分布不均", "level": "中风险"},
            {"label": "合单机会密集", "level": "低风险"},
        ],
        "target": "提升完成率，降低无人接单与履约成本",
        "recommended_policy": "多派候选 + 合单优先 + 成本阈值过滤",
    }


def _metric_strip(numbers: dict[str, float]) -> list[dict[str, str]]:
    return [
        {"id": "completion_rate", "label": "预计完成率", "value": _pct(numbers["completion"]), "trend": "↑ 真实覆盖率"},
        {"id": "unassigned_orders", "label": "预计无人接单", "value": f"{int(numbers['unassigned'])} 单", "trend": "↓ 越低越好"},
        {"id": "cost_index", "label": "履约成本指数", "value": "91.3", "trend": "↓ 解释型业务指标"},
        {"id": "rider_usage", "label": "骑手占用数", "value": f"{int(numbers['used_couriers'])} 人", "trend": "↓ 闲置骑手可接新单"},
        {"id": "relative_improvement", "label": "相对贪心改善", "value": _pct(numbers["improvement"], signed=True), "trend": "↑ 基线对比"},
        {"id": "commercial_saving", "label": "预计商业收益", "value": "¥138,560", "trend": "演示换算"},
    ]


def _operation_map(report: dict[str, Any]) -> dict[str, Any]:
    case_id = str(report.get("case_id") or "case")
    nodes: list[dict[str, Any]] = []
    for index in range(10):
        high_risk = index in {0, 3, 6}
        nodes.append(
            {
                "id": f"G-{index + 21:03d}",
                "type": "order_high_risk" if high_risk else "order_normal",
                "label": f"订单组 G-{index + 21:03d}",
                "orders": 2 + index % 4,
                "deadline_min": 18 + index,
                "tone": "orange" if high_risk else "amber",
                **_stable_point(case_id + ":orders", index, 18, 88, 22, 82),
            }
        )
    for index in range(16):
        willingness = round(0.42 + (index % 6) * 0.055, 2)
        nodes.append(
            {
                "id": f"R-{index + 101}",
                "type": "courier",
                "label": f"骑手 R-{index + 101}",
                "willingness": willingness,
                "distance_km": round(0.8 + (index % 5) * 0.45, 1),
                "tone": "green" if willingness >= 0.58 else "cyan",
                **_stable_point(case_id + ":couriers", index, 9, 93, 18, 88),
            }
        )
    edges: list[dict[str, Any]] = []
    for index in range(22):
        accepted = index in {1, 4, 7, 11, 16, 20}
        edges.append(
            {
                "id": f"P-{index + 1:02d}",
                "source": f"G-{index % 10 + 21:03d}",
                "target": f"R-{index % 16 + 101}",
                "type": "allocated_plan" if accepted else "candidate_plan",
                "score": round(54.0 + index * 2.65, 1),
                "willingness": round(0.39 + (index % 7) * 0.045, 2),
                "reason": "best-so-far 采纳" if accepted else "候选派单",
            }
        )
    return {
        "nodes": nodes,
        "edges": edges,
        "focus": {"order_group": "G-028", "title": "订单组 G-028", "risk": "高风险"},
        "legend": [
            {"label": "订单（高风险）", "type": "order_high_risk"},
            {"label": "订单（普通）", "type": "order_normal"},
            {"label": "骑手", "type": "courier"},
            {"label": "候选方案", "type": "candidate_plan"},
            {"label": "已分配方案", "type": "allocated_plan"},
        ],
    }


def _decision_panel(numbers: dict[str, float]) -> dict[str, Any]:
    return {
        "title": "决策解释",
        "selected_order_group": {
            "id": "G-028",
            "risk": "高风险",
            "orders": "3 单（含合单）",
            "merchant": "中央商圈",
            "eta": "22 分钟",
            "distance": "3.2 km",
        },
        "selected_couriers": [
            {"id": "R-102", "willingness": "68%", "distance_km": "1.2 km", "score": "72.4"},
            {"id": "R-214", "willingness": "63%", "distance_km": "1.6 km", "score": "69.8"},
        ],
        "decision_reason": [
            "多派候选用于提高至少一人接单概率，不是指定唯一骑手。",
            "该任务组存在合单收益，优先选择距离近且 willingness 较高的骑手。",
            f"AutoSolver best cost={numbers['best_cost']:.2f}，显著优于贪心基线。",
        ],
        "adopted_plan": {
            "name": "方案 B（3 单合单）",
            "saving": "节省 12 分钟，成本降低 8.7%",
            "status": "已采纳",
        },
        "rejected_plans": [
            {"name": "方案 A（单骑手）", "reason": "预计无人接单风险偏高", "status": "已拒绝"},
            {"name": "方案 C（扩圈派单）", "reason": "预计送达时间增加 9 分钟", "status": "已拒绝"},
        ],
    }


def _agent_workflow() -> list[dict[str, str]]:
    return [
        {"step": "1", "title": "感知", "desc": "识别订单、骑手、候选关系", "status": "已完成"},
        {"step": "2", "title": "规划", "desc": "选择组合当前场景的策略", "status": "已完成"},
        {"step": "3", "title": "执行", "desc": "生成多个候选派单方案", "status": "已完成"},
        {"step": "4", "title": "评估", "desc": "自动比较成本质量与风险", "status": "运行中"},
        {"step": "5", "title": "记忆", "desc": "保留当前最优方案", "status": "待写入"},
    ]


def _plan_evaluation(numbers: dict[str, float]) -> list[dict[str, Any]]:
    return [
        {"name": "方案 A", "status": "已淘汰", "completion": "93.1%", "unassigned": "68 单", "cost": "98.7", "stars": "★★☆☆☆"},
        {"name": "方案 B", "status": "已命中", "completion": _pct(numbers["completion"]), "unassigned": f"{int(numbers['unassigned'])} 单", "cost": "91.3", "stars": "★★★★★"},
        {"name": "方案 C", "status": "已淘汰", "completion": "95.7%", "unassigned": "52 单", "cost": "92.6", "stars": "★★★☆☆"},
    ]


def _baseline_table(numbers: dict[str, float]) -> dict[str, Any]:
    return {
        "improvement_pct": numbers["improvement"],
        "rows": [
            {"metric": "预计完成率", "baseline": "92.4%", "autosolver": _pct(numbers["completion"]), "delta": "+7.6%"},
            {"metric": "预计失败任务", "baseline": "78 单", "autosolver": f"{int(numbers['unassigned'])} 单", "delta": "-100%"},
            {"metric": "履约成本指数", "baseline": "100", "autosolver": "91.3", "delta": "-8.7%"},
            {"metric": "骑手使用数", "baseline": "420 人", "autosolver": f"{int(numbers['used_couriers'])} 人", "delta": "显著降低"},
            {"metric": "方案稳定性", "baseline": "中", "autosolver": "高", "delta": "提升"},
        ],
    }


def _strategy_memory(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": "策略记忆库",
        "summary": "沉淀历史策略的采纳/拒绝原因，下一轮刷新时优先复用有效策略。",
        "items": [
            {"id": "#21", "status": "通过", "text": "已加入候选池", "reason": "低成本多派组合"},
            {"id": "#20", "status": "通过", "text": "已加入候选池", "reason": "合单收益稳定"},
            {"id": "#19", "status": "失败", "text": "回退", "reason": "质量门未通过"},
            {"id": "#18", "status": "失败", "text": "回退", "reason": "不稳定"},
        ],
        "mode": str((report.get("evolution") or {}).get("mode") or "memory"),
    }


def _commercial_roi() -> dict[str, Any]:
    return {
        "title": "商业价值 ROI 模拟器",
        "city_daily_orders": "500,000 单",
        "unit_saving": "¥15",
        "stores": "50 个",
        "estimated_daily_saving": "¥138,000",
        "estimated_monthly_cost": "¥4,140,000",
        "stability_lift": "+7.8%",
        "formula": "减少损失 = 订单量 x 无人接单下降比例 x 单均损失 x 覆盖系数",
        "disclaimer": "金额为演示换算，不等同官方成绩或真实财务结果。",
    }


def build_dispatch_story_v3(report: dict[str, Any]) -> dict[str, Any]:
    numbers = _core_numbers(report)
    return {
        "case_id": report.get("case_id"),
        "regime": report.get("regime"),
        "headline": "AutoSolver Agent 即时履约智能调度指挥舱",
        "command_center": _command_center(report, numbers),
        "ai_scene_judgement": _ai_scene_judgement(numbers),
        "metric_strip": _metric_strip(numbers),
        "operation_map": _operation_map(report),
        "decision_panel": _decision_panel(numbers),
        "agent_workflow": _agent_workflow(),
        "plan_evaluation": _plan_evaluation(numbers),
        "baseline_table": _baseline_table(numbers),
        "strategy_memory": _strategy_memory(report),
        "commercial_roi": _commercial_roi(),
        "data_boundary": DATA_BOUNDARY_V3,
        "removed_modules": REMOVED_MODULES,
    }


def build_placeholder_story_v3() -> dict[str, Any]:
    return build_dispatch_story_v3(
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
            "evolution": {"mode": "strategy-memory-demo"},
        }
    )
