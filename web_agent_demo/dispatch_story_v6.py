from __future__ import annotations

from typing import Any

from web_agent_demo.dispatch_story_v5 import build_dispatch_story_v5


MEETING_BRIEF_V6 = {
    "source_scope": "会议纪要与视频前40分钟：围绕前端目标图、场景判断、基线指标、商业价值和演示边界展开。",
    "agreed_direction": "主交互必须是 AI 自动判断场景，并触发调度推理、地图聚焦、方案评估和策略记忆。",
    "baseline_rule": "纯贪心是必须出现的对照基线，AutoSolver 需要明确展示完成率、无人接单、成本和骑手占用改善。",
    "pitch_priority": "答辩优先讲商业落地：降低无人接单、减少履约成本、释放骑手继续接新单、沉淀可复用策略。",
    "dispatch_semantics": "多派候选是向多个候选骑手发出接单机会，提高至少一人接单概率，不是指定唯一骑手。",
    "removed_narratives": "取消不可信天气分区叙事、固定天气卡和左下安全回退大模块，避免评委质疑真实性。",
    "must_show": "策略记忆、动态刷新、点击商家/订单解释派单原因、绿色最优方案保留、黄色/红色方案淘汰。",
}


TARGET_FIDELITY_V6 = {
    "screen": "target_one_screen_1920x1080",
    "left_scene_count": 5,
    "top_scene_feature_count": 3,
    "central_map_weight": 0.56,
    "right_panel_density": "compact_decision_cards",
    "bottom_deck": "workflow_plan_baseline_memory_solver_roi",
}


def _scenario_focus_cards() -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "label": "午高峰爆单",
            "signal": "订单量激增 156%",
            "risk": "高风险",
            "icon": "bars",
            "focus_order": "G-028",
            "explain": "中心商圈订单密集，优先合单与多派候选。",
        },
        {
            "rank": 2,
            "label": "骑手供给紧张",
            "signal": "可用骑手 -18%",
            "risk": "高风险",
            "icon": "rider",
            "focus_order": "G-030",
            "explain": "供给不足时优先降低无人接单风险。",
        },
        {
            "rank": 3,
            "label": "商圈订单聚集",
            "signal": "核心商圈热区",
            "risk": "中风险",
            "icon": "building",
            "focus_order": "G-023",
            "explain": "订单密集但距离短，强调履约成本压缩。",
        },
        {
            "rank": 4,
            "label": "合单机会密集",
            "signal": "合单潜力 +37%",
            "risk": "低风险",
            "icon": "layers",
            "focus_order": "G-028",
            "explain": "多订单同向集中，是当前策略收益来源。",
        },
        {
            "rank": 5,
            "label": "新店突发订单",
            "signal": "新店订单突然增加",
            "risk": "中风险",
            "icon": "shop",
            "focus_order": "G-030",
            "explain": "突发需求进入候选池，但不压过核心高风险任务。",
        },
    ]


def _solver_evidence(story: dict[str, Any]) -> dict[str, str]:
    completion = next(item for item in story["metric_strip"] if item["id"] == "completion_rate")
    improvement = next(item for item in story["metric_strip"] if item["id"] == "relative_improvement")
    return {
        "title": "当前正式求解器",
        "solver": "AutoSolver v3.2.8",
        "status": "稳定运行中",
        "guardrail": "只写入通过质量门的候选池，避免坏策略污染记忆库。",
        "quality": f"覆盖率 {completion['value']}，相对贪心改善 {improvement['value']}。",
        "explain": "策略记忆只负责复用通过验证的调度经验，不再展示独立安全回退大模块。",
    }


def _operator_matrix(story: dict[str, Any]) -> list[dict[str, str]]:
    roi = story.get("commercial_playbook", {})
    return [
        {"label": "预计每日减少损失", "value": roi.get("daily_loss_reduction", "¥138,000")},
        {"label": "预计每月节省成本", "value": roi.get("monthly_cost_saving", "¥4,140,000")},
        {"label": "预计履约稳定性", "value": roi.get("stability_lift", "+7.8%")},
        {"label": "贪心基线锚点", "value": "纯贪心对照"},
    ]


def build_dispatch_story_v6(report: dict[str, Any]) -> dict[str, Any]:
    story = build_dispatch_story_v5(report)
    story["version"] = "v6-target-fidelity-briefed-dashboard"
    story["meeting_brief"] = MEETING_BRIEF_V6
    story["target_fidelity"] = TARGET_FIDELITY_V6
    story["scenario_focus_cards"] = _scenario_focus_cards()
    story["solver_evidence"] = _solver_evidence(story)
    story["operator_matrix"] = _operator_matrix(story)
    story["target_ui"] = {
        "stage": "1920x1080 fixed command center",
        "layout": "target one-screen command center with five scene cards, central map, decision explanation and proof deck",
        "reference": "目标界面图.png",
        "style_note": "进一步贴近目标图：左侧五场景、中心大地图、右侧紧凑解释、底部正式求解器与 ROI。",
    }
    return story


def build_placeholder_story_v6() -> dict[str, Any]:
    return build_dispatch_story_v6(
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
