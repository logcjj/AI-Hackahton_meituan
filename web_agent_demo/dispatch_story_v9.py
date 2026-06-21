from __future__ import annotations

from typing import Any

from web_agent_demo.dispatch_story_v8 import build_dispatch_story_v8


TARGET_DENSITY_AUDIT_V9 = {
    "intent": "目标图组件密度对齐：左侧 5 张业务场景卡、顶部 6 个 KPI、右侧 5 个决策解释块、底部 5 个答辩证据块。",
    "left_scene_cards": 5,
    "top_kpis": 6,
    "right_decision_blocks": 5,
    "bottom_proof_blocks": 5,
    "interaction_bias": "优先让评委按场景、决策、基线、商业价值四段理解，而不是在复杂算法细节里迷路。",
}


def _pitch_mode_tabs(story: dict[str, Any]) -> list[dict[str, str]]:
    metrics = {item["id"]: item["value"] for item in story["metric_strip"]}
    return [
        {
            "id": "scene",
            "label": "场景",
            "line": "AI 自动判断午高峰、供给紧张、合单机会，不依赖手动固定选择。",
        },
        {
            "id": "decision",
            "label": "决策",
            "line": "点击地图热区后解释多派候选、候选骑手、拒绝方案和接单概率逻辑。",
        },
        {
            "id": "baseline",
            "label": "基线",
            "line": f"对比纯贪心，完成率 {metrics['completion_rate']}，无人接单 {metrics['unassigned_orders']}，改善 {metrics['relative_improvement']}。",
        },
        {
            "id": "business",
            "label": "商业",
            "line": f"落到骑手占用减少、履约成本下降和预计商业收益 {metrics['commercial_saving']}。",
        },
    ]


def _decision_lens(story: dict[str, Any]) -> list[dict[str, str]]:
    roi = story["commercial_roi"]
    metrics = {item["id"]: item["value"] for item in story["metric_strip"]}
    return [
        {"label": "AI 场景", "value": "午高峰 + 供给紧张 + 合单机会", "tone": "cyan"},
        {"label": "派单语义", "value": "多派候选，提高至少一人接单概率", "tone": "green"},
        {"label": "淘汰逻辑", "value": "绿色最优保留，黄色/红色方案淡出", "tone": "yellow"},
        {"label": "贪心基线", "value": f"相对贪心改善 {metrics['relative_improvement']}", "tone": "blue"},
        {"label": "商业收口", "value": f"{roi['estimated_daily_saving']} / {roi['estimated_monthly_cost']}", "tone": "gold"},
    ]


def _judge_zone_map(story: dict[str, Any]) -> list[dict[str, str]]:
    matrix = {item["dimension"]: item for item in story["judge_evidence_matrix"]}
    return [
        {
            "dimension": "创新性",
            "zone": "中央地图 + 顶部 AI 场景识别",
            "visible_proof": matrix["创新性"]["proof"],
        },
        {
            "dimension": "完整性",
            "zone": "左侧场景卡 + 右侧决策解释 + 底部证据 dock",
            "visible_proof": matrix["完整性"]["proof"],
        },
        {
            "dimension": "应用效果",
            "zone": "顶部 KPI + Baseline vs AutoSolver 对比表",
            "visible_proof": matrix["应用效果"]["proof"],
        },
        {
            "dimension": "商业价值",
            "zone": "底部证据 dock + 商业价值 ROI 模拟器",
            "visible_proof": matrix["商业价值"]["proof"],
        },
    ]


def build_dispatch_story_v9(report: dict[str, Any]) -> dict[str, Any]:
    story = build_dispatch_story_v8(report)
    story["version"] = "v9-target-density-interaction-command-center"
    story["target_density_audit"] = TARGET_DENSITY_AUDIT_V9
    story["pitch_mode_tabs"] = _pitch_mode_tabs(story)
    story["decision_lens"] = _decision_lens(story)
    story["judge_zone_map"] = _judge_zone_map(story)
    story["target_ui"] = {
        "stage": "1920x1080 exact target dashboard",
        "layout": "target-density command center with scene meters, decision lens, proof dock and mode tabs",
        "reference": "目标界面图.png",
        "style_note": "v9 强化目标图组件密度、左侧场景仪表、右侧决策镜头、底部证据 dock 和答辩模式切换。",
    }
    story["visual_fidelity"] = {
        **story["visual_fidelity"],
        "left_scene_meters": 5,
        "right_decision_lens": 5,
        "bottom_proof_dock": 4,
        "mode_tabs": 4,
    }
    return story


def build_placeholder_story_v9() -> dict[str, Any]:
    return build_dispatch_story_v9(
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
