from __future__ import annotations

from typing import Any

from web_agent_demo.dispatch_story_v3 import build_dispatch_story_v3


MEETING_TAKEAWAYS = [
    "界面主线必须从固定场景按钮改为 AI 自动判断场景。",
    "地图保留订单、骑手、候选方案和已分配方案，不再展示右上固定天气卡。",
    "左下自进化安全回退大模块取消，改为策略记忆库展示历史策略沉淀。",
    "答辩重点放在商业落地、贪心基线对比、无人接单风险降低和成本节约。",
]


def _review_alignment(story: dict[str, Any]) -> list[dict[str, str]]:
    completion = next(item for item in story["metric_strip"] if item["id"] == "completion_rate")
    improvement = next(item for item in story["metric_strip"] if item["id"] == "relative_improvement")
    saving = next(item for item in story["metric_strip"] if item["id"] == "commercial_saving")
    return [
        {
            "dimension": "创新性",
            "evidence": "AI 自动推断午高峰、供给紧张、合单机会，并把策略选择解释到地图和决策面板。",
            "score_hook": "方案切入角度新颖，AI 与配送分配需求结合明确。",
        },
        {
            "dimension": "完整性",
            "evidence": "感知、规划、执行、评估、记忆闭环完整，页面覆盖场景、地图、决策、基线、ROI。",
            "score_hook": "功能逻辑闭环清晰，演示流程稳定。",
        },
        {
            "dimension": "应用效果",
            "evidence": f"真实样例覆盖率 {completion['value']}，相对贪心改善 {improvement['value']}。",
            "score_hook": "响应及时，指标来自 Agent 报告和派生解释口径。",
        },
        {
            "dimension": "商业价值",
            "evidence": f"预计收益 {saving['value']}，展示无人接单下降、骑手占用降低和履约成本改善。",
            "score_hook": "能解释经济效益、运营价值和长期策略记忆价值。",
        },
    ]


def build_dispatch_story_v4(report: dict[str, Any]) -> dict[str, Any]:
    story = build_dispatch_story_v3(report)
    story["version"] = "v4-target-dashboard"
    story["meeting_takeaways"] = MEETING_TAKEAWAYS
    story["review_alignment"] = _review_alignment(story)
    story["target_ui"] = {
        "stage": "1920x1080 fixed command center",
        "layout": "top header + KPI strip + left scene rail + central map + right decision panel + bottom evidence deck",
        "reference": "目标界面图.png",
    }
    return story


def build_placeholder_story_v4() -> dict[str, Any]:
    return build_dispatch_story_v4(
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
