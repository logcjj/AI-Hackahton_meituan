from __future__ import annotations

from typing import Any

from web_agent_demo.dispatch_story_v7 import build_dispatch_story_v7


TARGET_SCREEN_CONTRACT_V8 = {
    "stage": "1920x1080 exact target dashboard",
    "visual_language": "角标边框、霓虹分割线、卫星地图底纹、流动派单路径、热区光圈、密集数据卡片",
    "removed_from_target": "取消右上固定天气卡；取消左下自进化安全回退大模块；避免局部雨天低接单叙事。",
    "kept_from_meeting": "AI 自动判断场景、策略记忆库、贪心基线对比、商业价值量化、多派候选语义。",
}


def _demo_runbook(story: dict[str, Any]) -> list[dict[str, str]]:
    metrics = {item["id"]: item["value"] for item in story["metric_strip"]}
    return [
        {
            "step": "01",
            "title": "刷新态势",
            "line": "刷新后先展示任务、骑手、候选关系和热区，不手动指定业务场景。",
        },
        {
            "step": "02",
            "title": "开始推理",
            "line": "AI 自动判断午高峰、供给紧张、合单机会，并生成候选派单方案。",
        },
        {
            "step": "03",
            "title": "地图聚焦",
            "line": "点击业务场景后聚焦订单组，右侧解释多派候选骑手、风险和原因。",
        },
        {
            "step": "04",
            "title": "方案淘汰",
            "line": "黄色/红色方案被淡出，绿色最优方案保留，并写入策略记忆。",
        },
        {
            "step": "05",
            "title": "讲基线",
            "line": f"纯贪心作为对照，AutoSolver 完成率 {metrics['completion_rate']}，无人接单 {metrics['unassigned_orders']}。",
        },
        {
            "step": "06",
            "title": "讲商业价值",
            "line": f"最后落到成本节约、骑手占用减少和预计商业收益 {metrics['commercial_saving']}。",
        },
    ]


def _interaction_contract() -> dict[str, str]:
    return {
        "primary_action": "点击开始推理后由 AI 自动判断场景，不让评委误解为手动选择固定场景。",
        "dispatch_semantics": "多派候选是向多个候选骑手发出接单机会，提高至少一人接单概率，不是指定唯一骑手。",
        "map_click": "点击业务场景后聚焦订单组，地图、右侧决策解释和底部证据同步更新。",
        "plan_animation": "绿色最优方案保留，黄色/红色候选方案淘汰淡出，形成一眼能懂的决策过程。",
        "baseline": "始终保留纯贪心基线，解释完成率、无人接单、履约成本和骑手占用的改善。",
        "business_close": "商业价值只作为脱敏沙盘换算，明确边界，避免把演示金额包装成真实财务结论。",
    }


def _judge_evidence_matrix(story: dict[str, Any]) -> list[dict[str, str]]:
    metrics = {item["id"]: item["value"] for item in story["metric_strip"]}
    return [
        {
            "dimension": "创新性",
            "metric": "AI + 即时履约调度",
            "proof": "AI 自动判断复杂配送场景，并把多派候选、合单优先和策略记忆串成解释链路。",
            "screen": "顶部场景识别 + 地图热区 + 右侧决策解释",
        },
        {
            "dimension": "完整性",
            "metric": "感知-规划-执行-评估-记忆闭环",
            "proof": "一屏覆盖输入态势、候选派单、方案淘汰、基线对比、策略记忆和 ROI。",
            "screen": "左侧业务场景 + 中央地图 + 底部证据区",
        },
        {
            "dimension": "应用效果",
            "metric": f"{metrics['completion_rate']} / {metrics['unassigned_orders']} / {metrics['relative_improvement']}",
            "proof": "用真实样例字段与派生解释指标展示完成率、无人接单和相对贪心改善。",
            "screen": "顶部 KPI + Baseline vs AutoSolver",
        },
        {
            "dimension": "商业价值",
            "metric": f"{metrics['commercial_saving']} 预计收益",
            "proof": "把无人接单下降、骑手占用减少和履约成本改善转换为运营可理解的收益口径。",
            "screen": "商业价值 ROI 模拟器 + 答辩导航",
        },
    ]


def build_dispatch_story_v8(report: dict[str, Any]) -> dict[str, Any]:
    story = build_dispatch_story_v7(report)
    story["version"] = "v8-target-match-pitch-command-center"
    story["target_screen_contract"] = TARGET_SCREEN_CONTRACT_V8
    story["demo_runbook"] = _demo_runbook(story)
    story["interaction_contract"] = _interaction_contract()
    story["judge_evidence_matrix"] = _judge_evidence_matrix(story)
    story["target_ui"] = {
        "stage": "1920x1080 exact target dashboard",
        "layout": "target-identical command center with frame overlay, pitch navigator and judge matrix",
        "reference": "目标界面图.png",
        "style_note": "v8 在 v7 路网基础上补齐目标图的一屏大屏骨架、角标边框、热区光圈、演示导览和评审矩阵。",
    }
    story["visual_fidelity"] = {
        **story["visual_fidelity"],
        "target_frame": "corner-bracket-bezel",
        "heat_rings": 3,
        "pitch_navigator": 6,
        "judge_matrix_cards": 4,
    }
    return story


def build_placeholder_story_v8() -> dict[str, Any]:
    return build_dispatch_story_v8(
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
