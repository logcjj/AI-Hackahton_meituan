from __future__ import annotations

import unittest
from unittest import mock


class DispatchStoryV10Test(unittest.TestCase):
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

    def test_story_v10_adds_top_alerts_and_target_callout(self):
        from web_agent_demo.dispatch_story_v10 import build_dispatch_story_v10

        story = build_dispatch_story_v10(self._sample_report())

        self.assertEqual(story["version"], "v10-target-exact-narrative-command-center")
        self.assertEqual(len(story["top_alert_cards"]), 3)
        self.assertEqual([item["label"] for item in story["top_alert_cards"]], ["午高峰爆单", "骑手供给紧张", "合单机会密集"])
        self.assertIn("订单组 G-028", story["target_map_callout"]["title"])
        self.assertIn("多派候选", story["target_map_callout"]["dispatch_semantics"])
        self.assertNotIn("雨天低接单意愿", str(story))
        self.assertNotIn("Self-Evolving Code Loop", str(story))

    def test_story_v10_separates_real_derived_and_demo_data_boundaries(self):
        from web_agent_demo.dispatch_story_v10 import build_dispatch_story_v10

        story = build_dispatch_story_v10(self._sample_report())

        labels = [item["label"] for item in story["data_truth_rail"]]
        self.assertEqual(labels, ["真实输入", "派生解释", "演示映射"])
        self.assertIn("任务/骑手/候选行", story["data_truth_rail"][0]["items"])
        self.assertIn("贪心基线对比", story["data_truth_rail"][1]["items"])
        self.assertIn("地图坐标", story["data_truth_rail"][2]["items"])
        self.assertIn("边界", story["data_truth_rail"][2]["note"])

    def test_story_v10_contains_presenter_script_for_judge_flow(self):
        from web_agent_demo.dispatch_story_v10 import build_dispatch_story_v10

        story = build_dispatch_story_v10(self._sample_report())

        self.assertEqual(len(story["presenter_script"]), 5)
        self.assertIn("创新性", story["presenter_script"][0]["judge"])
        self.assertIn("完整性", story["presenter_script"][1]["judge"])
        self.assertIn("应用效果", story["presenter_script"][3]["judge"])
        self.assertIn("商业价值", story["presenter_script"][4]["judge"])
        self.assertIn("贪心", str(story["presenter_script"]))
        self.assertIn("¥", str(story["presenter_script"]))

    def test_dispatch_v10_page_has_target_exact_narrative_hooks(self):
        from web_agent_demo.server_dispatch_v10 import render_dispatch_index_v10

        html = render_dispatch_index_v10()

        self.assertIn("v10-exact-narrative-shell", html)
        self.assertIn("function renderV10TopAlerts", html)
        self.assertIn("function renderV10MapCallout", html)
        self.assertIn("function renderV10DataTruthRail", html)
        self.assertIn("function renderV10PresenterScript", html)
        self.assertIn("function renderV10DecisionFocus", html)
        self.assertIn("data-testid=\"v10-top-alerts\"", html)
        self.assertIn("data-testid=\"v10-map-callout\"", html)
        self.assertIn("data-testid=\"v10-data-truth-rail\"", html)
        self.assertIn("data-testid=\"v10-presenter-script\"", html)
        self.assertIn("data-testid=\"v10-decision-focus\"", html)
        self.assertIn("class=\"v10-alert-card\"", html)
        self.assertIn("class=\"v10-truth-badge\"", html)
        self.assertNotIn("雨天低接单意愿", html)
        self.assertNotIn("Self-Evolving Code Loop", html)

    def test_dispatch_v10_payload_wraps_report_with_v10_story(self):
        from web_agent_demo import server_dispatch_v10

        with mock.patch.object(server_dispatch_v10, "run_case_agent", return_value=self._sample_report()):
            payload = server_dispatch_v10.build_dispatch_payload_v10("large_seed301", budget_s=10.0)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["story"]["version"], "v10-target-exact-narrative-command-center")
        self.assertEqual(payload["story"]["case_id"], "large_seed301")
        self.assertNotIn("path", payload["story"])


if __name__ == "__main__":
    unittest.main()
