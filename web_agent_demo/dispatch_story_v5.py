from __future__ import annotations

from typing import Any

from web_agent_demo.dispatch_story_v4 import build_dispatch_story_v4


MEETING_UNDERSTANDING_V5 = {
    "primary_interaction": "AI 自动场景判断驱动全屏指挥舱，而不是让评委手动选择业务场景。",
    "dispatch_semantics": "多派候选用于提高至少一名骑手接单的概率，不是指定唯一骑手。",
    "must_keep": "策略记忆库要保留并前置为可讲述的策略沉淀证据。",
    "pitch_focus": "商业落地、贪心基线对比、无人接单风险降低、成本节约。",
    "removed": "取消右上固定天气卡与左下大块自进化安全模块，避免偏离主线。",
}


VISUAL_CONTRACT_V5 = {
    "layout": "top command bar + KPI evidence strip + left scene rail + large operation map + right decision explanation + bottom proof deck",
    "map_style": "dark_meituan_operation_map",
    "interaction": "click_order_group_updates_decision_panel",
    "evidence_style": "judge_standard_proof_bar",
}


def _interactive_hotspots(story: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "order_group": "G-028",
            "risk": "高风险",
            "candidate_count": 3,
            "eta": "22 分钟",
            "summary": "中央商圈 3 单合单，优先多派高意愿近距离骑手。",
            "couriers": [
                {"id": "R-102", "willingness": "68%", "distance": "1.2 km", "score": "72.4"},
                {"id": "R-214", "willingness": "63%", "distance": "1.6 km", "score": "69.8"},
            ],
            "reasons": [
                "多派候选不是指定唯一骑手，而是提高至少一人接单概率。",
                "合单收益高，预计比单骑手方案节省 12 分钟。",
                "当前 best cost 明显低于贪心基线。",
            ],
        },
        {
            "order_group": "G-023",
            "risk": "中风险",
            "candidate_count": 4,
            "eta": "18 分钟",
            "summary": "订单密集但距离短，适合合单优先与低成本过滤。",
            "couriers": [
                {"id": "R-105", "willingness": "64%", "distance": "0.9 km", "score": "75.1"},
                {"id": "R-110", "willingness": "58%", "distance": "1.4 km", "score": "68.6"},
            ],
            "reasons": [
                "候选关系充足，优先压缩履约成本指数。",
                "保留备选骑手，避免主候选拒单后重新搜索。",
                "与历史策略 #20 的合单收益稳定模式匹配。",
            ],
        },
        {
            "order_group": "G-030",
            "risk": "高风险",
            "candidate_count": 2,
            "eta": "26 分钟",
            "summary": "边缘热区候选偏少，扩圈只作为兜底方案。",
            "couriers": [
                {"id": "R-112", "willingness": "70%", "distance": "2.1 km", "score": "71.0"},
                {"id": "R-116", "willingness": "58%", "distance": "2.4 km", "score": "63.8"},
            ],
            "reasons": [
                "供给紧张场景下优先保障无人接单风险下降。",
                "扩圈会增加 ETA，因此只进入未采纳方案池。",
                "策略记忆库建议复用低成本多派组合。",
            ],
        },
    ]


def _judge_evidence_bar(story: dict[str, Any]) -> list[dict[str, str]]:
    review_items = story.get("review_alignment", [])
    return [
        {
            "dimension": item["dimension"],
            "headline": item["score_hook"],
            "proof": item["evidence"],
        }
        for item in review_items
    ]


def _commercial_playbook(story: dict[str, Any]) -> dict[str, Any]:
    roi = story.get("commercial_roi", {})
    return {
        "title": "商业落地口径",
        "daily_loss_reduction": roi.get("estimated_daily_saving", "¥138,000"),
        "monthly_cost_saving": roi.get("estimated_monthly_cost", "¥4,140,000"),
        "stability_lift": roi.get("stability_lift", "+7.8%"),
        "baseline_anchor": "贪心基线用于说明没有 Agent 时的无人接单与成本损失。",
        "demo_boundary": "金额只做沙盘换算，算法有效性以覆盖率、成本、拒单风险等指标解释。",
    }


def build_dispatch_story_v5(report: dict[str, Any]) -> dict[str, Any]:
    story = build_dispatch_story_v4(report)
    story["version"] = "v5-target-interactive-dashboard"
    story["meeting_understanding"] = MEETING_UNDERSTANDING_V5
    story["visual_contract"] = VISUAL_CONTRACT_V5
    story["interactive_hotspots"] = _interactive_hotspots(story)
    story["judge_evidence_bar"] = _judge_evidence_bar(story)
    story["commercial_playbook"] = _commercial_playbook(story)
    story["target_ui"] = {
        "stage": "1920x1080 fixed command center",
        "layout": VISUAL_CONTRACT_V5["layout"],
        "reference": "目标界面图.png",
        "style_note": "目标图风格：深色城市地图、霓虹线路、左侧业务场景、右侧决策解释、底部证据卡。",
    }
    return story


def build_placeholder_story_v5() -> dict[str, Any]:
    return build_dispatch_story_v5(
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
