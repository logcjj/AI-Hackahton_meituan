from __future__ import annotations

import unittest
from unittest import mock


class DispatchStoryV5Test(unittest.TestCase):
    def _sample_report(self):
        return {
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
                "uncovered_tasks": [],
                "riders_per_group": {"1": 3, "2": 34, "3": 3},
                "tasks_per_group": {"1": 40},
                "invalid_reasons": [],
            },
            "rounds": [
                {
                    "round": 1,
                    "reason": "initial diverse exploration",
                    "strategies": [
                        {
                            "name": "greedy_baseline",
                            "label": "贪心基线",
                            "local_cost": 2097.657539,
                            "valid": True,
                            "covered_tasks": 40,
                            "total_tasks": 40,
                            "groups": 40,
                            "elapsed_ms": 34.171,
                            "accepted": True,
                        },
                        {
                            "name": "production_solver",
                            "label": "生产级综合求解器",
                            "local_cost": 657.1040208060375,
                            "valid": True,
                            "covered_tasks": 40,
                            "total_tasks": 40,
                            "groups": 40,
                            "elapsed_ms": 3964.407,
                            "accepted": True,
                        },
                    ],
                }
            ],
            "events": [
                {"type": "perception", "message": "识别为 large 场景"},
                {"type": "strategy_eval", "strategy": "greedy_baseline"},
                {"type": "best_update", "strategy": "production_solver"},
            ],
            "evolution": {"mode": "experimental-track-no-solver-mutation"},
        }

    def test_story_v5_captures_meeting_understanding_and_target_contract(self):
        from web_agent_demo.dispatch_story_v5 import build_dispatch_story_v5

        story = build_dispatch_story_v5(self._sample_report())

        self.assertEqual(story["version"], "v5-target-interactive-dashboard")
        self.assertEqual(story["target_ui"]["reference"], "目标界面图.png")
        self.assertEqual(story["target_ui"]["stage"], "1920x1080 fixed command center")
        self.assertIn("AI 自动场景判断", story["meeting_understanding"]["primary_interaction"])
        self.assertIn("多派候选", story["meeting_understanding"]["dispatch_semantics"])
        self.assertIn("策略记忆库", story["meeting_understanding"]["must_keep"])
        self.assertIn("商业落地", story["meeting_understanding"]["pitch_focus"])
        self.assertNotIn("雨天低接单意愿", str(story))
        self.assertNotIn("Self-Evolving Code Loop", str(story))

    def test_story_v5_adds_interactive_map_hotspots_and_business_evidence(self):
        from web_agent_demo.dispatch_story_v5 import build_dispatch_story_v5

        story = build_dispatch_story_v5(self._sample_report())

        self.assertGreaterEqual(len(story["interactive_hotspots"]), 3)
        self.assertIn("G-028", {item["order_group"] for item in story["interactive_hotspots"]})
        self.assertTrue(all(item["candidate_count"] >= 2 for item in story["interactive_hotspots"]))
        self.assertGreaterEqual(len(story["judge_evidence_bar"]), 4)
        self.assertIn("创新性", {item["dimension"] for item in story["judge_evidence_bar"]})
        self.assertIn("商业价值", {item["dimension"] for item in story["judge_evidence_bar"]})
        self.assertEqual(story["visual_contract"]["map_style"], "dark_meituan_operation_map")
        self.assertEqual(story["visual_contract"]["interaction"], "click_order_group_updates_decision_panel")

    def test_dispatch_v5_page_contains_visual_upgrade_and_interaction_hooks(self):
        from web_agent_demo.server_dispatch_v5 import render_dispatch_index_v5

        html = render_dispatch_index_v5()

        self.assertIn("v5-target-dashboard", html)
        self.assertIn("--map-satellite", html)
        self.assertIn("function enhanceV5Interactions", html)
        self.assertIn("function selectOrderGroup", html)
        self.assertIn("class=\"hit-target\"", html)
        self.assertIn("addEventListener('click'", html)
        self.assertIn("id=\"v5-judge-evidence\"", html)
        self.assertIn("评审证据栏", html)
        self.assertIn("目标图风格", html)
        self.assertIn("多派候选不是指定唯一骑手", html)
        self.assertNotIn("Self-Evolving Code Loop", html)
        self.assertNotIn("雨天低接单意愿", html)

    def test_dispatch_v5_payload_wraps_report_with_v5_story(self):
        from web_agent_demo import server_dispatch_v5

        with mock.patch.object(server_dispatch_v5, "run_case_agent", return_value=self._sample_report()):
            payload = server_dispatch_v5.build_dispatch_payload_v5("large_seed301", budget_s=10.0)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["story"]["version"], "v5-target-interactive-dashboard")
        self.assertEqual(payload["story"]["case_id"], "large_seed301")
        self.assertNotIn("path", payload["story"])


if __name__ == "__main__":
    unittest.main()
