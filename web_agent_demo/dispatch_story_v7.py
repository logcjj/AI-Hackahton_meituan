from __future__ import annotations

from typing import Any

from web_agent_demo.dispatch_story_v6 import build_dispatch_story_v6


VISUAL_FIDELITY_V7 = {
    "intent": "目标图运营地图质感：深色城市道路、河道、热区光圈、流动派单路径和答辩证据条。",
    "road_layers": 4,
    "kpi_micro_charts": 6,
    "decision_ticker": "scenario_to_plan_to_baseline_to_roi",
}


def _map_road_layers() -> list[dict[str, Any]]:
    return [
        {
            "id": "river-south",
            "kind": "river",
            "path": "M 2 78 C 16 70, 28 83, 43 74 S 70 69, 98 76",
            "width": 3.2,
        },
        {
            "id": "ring-east",
            "kind": "major",
            "path": "M 70 4 C 62 20, 62 38, 76 52 S 88 75, 78 96",
            "width": 1.2,
        },
        {
            "id": "avenue-center",
            "kind": "major",
            "path": "M 8 46 C 24 42, 34 50, 49 43 S 78 36, 96 44",
            "width": 1.1,
        },
        {
            "id": "grid-west",
            "kind": "minor",
            "path": "M 14 10 L 34 92 M 4 32 L 61 20 M 12 62 L 60 55 M 42 6 L 28 94",
            "width": 0.55,
        },
        {
            "id": "grid-east",
            "kind": "minor",
            "path": "M 58 12 L 94 84 M 54 31 L 97 25 M 55 64 L 98 58 M 82 8 L 68 96",
            "width": 0.55,
        },
    ]


def _pitch_storyboard(story: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"beat": "开场", "line": "AutoSolver Agent 在 10 秒内完成场景识别、推理和证据输出。"},
        {"beat": "AI 场景判断", "line": "系统自动识别午高峰、供给紧张、合单机会，不依赖手动切换。"},
        {"beat": "地图聚焦", "line": "点击业务场景后聚焦订单组，展示多派候选路径和风险解释。"},
        {"beat": "方案淘汰", "line": "黄色/红色候选方案被淘汰，绿色最优方案保留并写入策略记忆。"},
        {"beat": "基线对比", "line": "纯贪心作为基准，对比完成率、无人接单、成本和骑手占用。"},
        {"beat": "商业价值", "line": f"预计商业收益 {story['commercial_roi']['estimated_daily_saving']}，强调履约稳定性和成本节约。"},
    ]


def _judge_ribbon(story: dict[str, Any]) -> list[dict[str, str]]:
    metrics = {item["id"]: item["value"] for item in story["metric_strip"]}
    return [
        {
            "dimension": "创新性",
            "hook": "AI + 即时履约调度",
            "proof": "AI 自动判断复杂业务场景，并把多派候选、合单优先和策略记忆合成一条可解释链路。",
        },
        {
            "dimension": "完整性",
            "hook": "端到端闭环",
            "proof": "感知、规划、执行、评估、记忆、商业价值都在同一屏闭环展示。",
        },
        {
            "dimension": "应用效果",
            "hook": "优于纯贪心",
            "proof": f"完成率 {metrics['completion_rate']}，无人接单 {metrics['unassigned_orders']}，相对贪心改善 {metrics['relative_improvement']}。",
        },
        {
            "dimension": "商业价值",
            "hook": "可量化收益",
            "proof": f"预计收益 {metrics['commercial_saving']}，并释放骑手占用、降低履约成本。",
        },
    ]


def build_dispatch_story_v7(report: dict[str, Any]) -> dict[str, Any]:
    story = build_dispatch_story_v6(report)
    story["version"] = "v7-target-polish-command-center"
    story["visual_fidelity"] = VISUAL_FIDELITY_V7
    story["map_road_layers"] = _map_road_layers()
    story["pitch_storyboard"] = _pitch_storyboard(story)
    story["judge_ribbon"] = _judge_ribbon(story)
    story["target_ui"] = {
        "stage": "1920x1080 fixed command center",
        "layout": "target-like polished command center with road map layers, KPI micro charts and judge ribbon",
        "reference": "目标界面图.png",
        "style_note": "v7 强化地图道路层、KPI 微图、评审证据条和方案淘汰动效。",
    }
    return story


def build_placeholder_story_v7() -> dict[str, Any]:
    return build_dispatch_story_v7(
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
