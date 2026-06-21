from __future__ import annotations

import unittest
from unittest import mock


class DispatchStoryV6Test(unittest.TestCase):
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

    def test_story_v6_turns_first_40_minutes_into_product_brief(self):
        from web_agent_demo.dispatch_story_v6 import build_dispatch_story_v6

        story = build_dispatch_story_v6(self._sample_report())

        self.assertEqual(story["version"], "v6-target-fidelity-briefed-dashboard")
        self.assertIn("前40分钟", story["meeting_brief"]["source_scope"])
        self.assertIn("AI 自动判断", story["meeting_brief"]["agreed_direction"])
        self.assertIn("纯贪心", story["meeting_brief"]["baseline_rule"])
        self.assertIn("商业落地", story["meeting_brief"]["pitch_priority"])
        self.assertIn("多派候选", story["meeting_brief"]["dispatch_semantics"])
        self.assertNotIn("局部雨天", story["meeting_brief"]["removed_narratives"])
        self.assertIn("策略记忆", story["meeting_brief"]["must_show"])

    def test_story_v6_matches_target_screen_modules_without_cancelled_blocks(self):
        from web_agent_demo.dispatch_story_v6 import build_dispatch_story_v6

        story = build_dispatch_story_v6(self._sample_report())

        self.assertEqual(story["target_fidelity"]["screen"], "target_one_screen_1920x1080")
        self.assertEqual(story["target_fidelity"]["left_scene_count"], 5)
        self.assertEqual(story["target_fidelity"]["top_scene_feature_count"], 3)
        self.assertGreaterEqual(story["target_fidelity"]["central_map_weight"], 0.52)
        self.assertEqual(len(story["scenario_focus_cards"]), 5)
        self.assertIn("新店突发订单", {item["label"] for item in story["scenario_focus_cards"]})
        self.assertEqual(story["solver_evidence"]["solver"], "AutoSolver v3.2.8")
        self.assertIn("只写入通过质量门的候选池", story["solver_evidence"]["guardrail"])
        dumped = str(story)
        self.assertNotIn("Self-Evolving Code Loop", dumped)
        self.assertNotIn("雨天低接单意愿", dumped)

    def test_dispatch_v6_page_has_target_fidelity_hooks(self):
        from web_agent_demo.server_dispatch_v6 import render_dispatch_index_v6

        html = render_dispatch_index_v6()

        self.assertIn("v6-exact-target-shell", html)
        self.assertIn("业务场景选择", html)
        self.assertIn("当前正式求解器", html)
        self.assertIn("调度目标", html)
        self.assertIn("function renderV6ScenarioRail", html)
        self.assertIn("function focusScenarioArea", html)
        self.assertIn("function renderV6SolverEvidence", html)
        self.assertIn("function playDecisionTimeline", html)
        self.assertIn("function updateScaleV6", html)
        self.assertIn("Math.min((window.innerWidth - 20) / 1920, (window.innerHeight - 16) / 1080)", html)
        self.assertIn("data-testid=\"v6-main-map\"", html)
        self.assertIn("data-testid=\"v6-solver-card\"", html)
        self.assertNotIn("Self-Evolving Code Loop", html)
        self.assertNotIn("雨天低接单意愿", html)

    def test_dispatch_v6_payload_wraps_report_with_v6_story(self):
        from web_agent_demo import server_dispatch_v6

        with mock.patch.object(server_dispatch_v6, "run_case_agent", return_value=self._sample_report()):
            payload = server_dispatch_v6.build_dispatch_payload_v6("large_seed301", budget_s=10.0)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["story"]["version"], "v6-target-fidelity-briefed-dashboard")
        self.assertEqual(payload["story"]["case_id"], "large_seed301")
        self.assertNotIn("path", payload["story"])


if __name__ == "__main__":
    unittest.main()
