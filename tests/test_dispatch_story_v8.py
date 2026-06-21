from __future__ import annotations

import unittest
from unittest import mock


class DispatchStoryV8Test(unittest.TestCase):
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

    def test_story_v8_adds_target_screen_contract_without_cancelled_modules(self):
        from web_agent_demo.dispatch_story_v8 import build_dispatch_story_v8

        story = build_dispatch_story_v8(self._sample_report())

        self.assertEqual(story["version"], "v8-target-match-pitch-command-center")
        self.assertEqual(story["target_screen_contract"]["stage"], "1920x1080 exact target dashboard")
        self.assertIn("角标边框", story["target_screen_contract"]["visual_language"])
        self.assertIn("卫星地图", story["target_screen_contract"]["visual_language"])
        self.assertIn("取消右上固定天气卡", story["target_screen_contract"]["removed_from_target"])
        self.assertIn("取消左下自进化安全回退大模块", story["target_screen_contract"]["removed_from_target"])
        self.assertNotIn("Self-Evolving Code Loop", str(story))
        self.assertNotIn("雨天低接单意愿", str(story))

    def test_story_v8_turns_meeting_into_demo_runbook_and_interaction_contract(self):
        from web_agent_demo.dispatch_story_v8 import build_dispatch_story_v8

        story = build_dispatch_story_v8(self._sample_report())

        runbook_titles = [item["title"] for item in story["demo_runbook"]]
        self.assertEqual(runbook_titles, ["刷新态势", "开始推理", "地图聚焦", "方案淘汰", "讲基线", "讲商业价值"])
        self.assertIn("AI 自动判断", story["demo_runbook"][1]["line"])
        self.assertIn("多派候选", story["interaction_contract"]["dispatch_semantics"])
        self.assertIn("点击业务场景后聚焦订单组", story["interaction_contract"]["map_click"])
        self.assertIn("绿色最优方案保留", story["interaction_contract"]["plan_animation"])
        self.assertIn("贪心", story["interaction_contract"]["baseline"])

    def test_story_v8_repackages_judging_into_dense_evidence_matrix(self):
        from web_agent_demo.dispatch_story_v8 import build_dispatch_story_v8

        story = build_dispatch_story_v8(self._sample_report())

        dimensions = [item["dimension"] for item in story["judge_evidence_matrix"]]
        self.assertEqual(dimensions, ["创新性", "完整性", "应用效果", "商业价值"])
        self.assertTrue(all(item["metric"] for item in story["judge_evidence_matrix"]))
        self.assertTrue(all(item["proof"] for item in story["judge_evidence_matrix"]))
        self.assertIn("100.0%", str(story["judge_evidence_matrix"]))
        self.assertIn("¥", str(story["judge_evidence_matrix"]))

    def test_dispatch_v8_page_has_exact_target_match_hooks(self):
        from web_agent_demo.server_dispatch_v8 import render_dispatch_index_v8

        html = render_dispatch_index_v8()

        self.assertIn("v8-target-match-shell", html)
        self.assertIn("function renderV8TargetFrame", html)
        self.assertIn("function renderV8PitchNavigator", html)
        self.assertIn("function renderV8JudgeMatrix", html)
        self.assertIn("function renderV8FlowCanvas", html)
        self.assertIn("data-testid=\"v8-target-frame\"", html)
        self.assertIn("data-testid=\"v8-pitch-navigator\"", html)
        self.assertIn("data-testid=\"v8-judge-matrix\"", html)
        self.assertIn("data-testid=\"v8-flow-canvas\"", html)
        self.assertIn("class=\"v8-corner tl\"", html)
        self.assertIn("class=\"v8-heat-ring\"", html)
        self.assertIn("class=\"v8-evidence-card\"", html)
        self.assertNotIn("Self-Evolving Code Loop", html)
        self.assertNotIn("雨天低接单意愿", html)

    def test_dispatch_v8_payload_wraps_report_with_v8_story(self):
        from web_agent_demo import server_dispatch_v8

        with mock.patch.object(server_dispatch_v8, "run_case_agent", return_value=self._sample_report()):
            payload = server_dispatch_v8.build_dispatch_payload_v8("large_seed301", budget_s=10.0)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["story"]["version"], "v8-target-match-pitch-command-center")
        self.assertEqual(payload["story"]["case_id"], "large_seed301")
        self.assertNotIn("path", payload["story"])


if __name__ == "__main__":
    unittest.main()
