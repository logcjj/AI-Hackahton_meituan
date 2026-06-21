from __future__ import annotations

import unittest
from unittest import mock


class DispatchStoryV7Test(unittest.TestCase):
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

    def test_story_v7_adds_visual_fidelity_layers_and_pitch_storyboard(self):
        from web_agent_demo.dispatch_story_v7 import build_dispatch_story_v7

        story = build_dispatch_story_v7(self._sample_report())

        self.assertEqual(story["version"], "v7-target-polish-command-center")
        self.assertEqual(story["visual_fidelity"]["road_layers"], 4)
        self.assertEqual(story["visual_fidelity"]["kpi_micro_charts"], 6)
        self.assertIn("目标图运营地图质感", story["visual_fidelity"]["intent"])
        self.assertGreaterEqual(len(story["map_road_layers"]), 4)
        self.assertGreaterEqual(len(story["pitch_storyboard"]), 6)
        self.assertIn("开场", story["pitch_storyboard"][0]["beat"])
        self.assertIn("商业价值", story["pitch_storyboard"][-1]["beat"])

    def test_story_v7_repackages_review_criteria_as_judge_ribbon(self):
        from web_agent_demo.dispatch_story_v7 import build_dispatch_story_v7

        story = build_dispatch_story_v7(self._sample_report())

        dimensions = {item["dimension"] for item in story["judge_ribbon"]}
        self.assertEqual(dimensions, {"创新性", "完整性", "应用效果", "商业价值"})
        self.assertTrue(all(item["proof"] for item in story["judge_ribbon"]))
        self.assertIn("AI 自动判断", story["judge_ribbon"][0]["proof"])
        self.assertIn("贪心", str(story["judge_ribbon"]))
        self.assertIn("¥", str(story["judge_ribbon"]))
        self.assertNotIn("Self-Evolving Code Loop", str(story))
        self.assertNotIn("雨天低接单意愿", str(story))

    def test_dispatch_v7_page_has_polished_map_and_presentation_hooks(self):
        from web_agent_demo.server_dispatch_v7 import render_dispatch_index_v7

        html = render_dispatch_index_v7()

        self.assertIn("v7-polish-shell", html)
        self.assertIn("function renderV7RoadNetwork", html)
        self.assertIn("function renderV7KpiMicroCharts", html)
        self.assertIn("function renderV7JudgeRibbon", html)
        self.assertIn("function triggerV7PlanElimination", html)
        self.assertIn("data-testid=\"v7-road-layer\"", html)
        self.assertIn("data-testid=\"v7-judge-ribbon\"", html)
        self.assertIn("data-testid=\"v7-decision-ticker\"", html)
        self.assertIn("class=\"v7-road major\"", html)
        self.assertIn("class=\"v7-road river\"", html)
        self.assertIn("class=\"v7-kpi-micro\"", html)
        self.assertNotIn("Self-Evolving Code Loop", html)
        self.assertNotIn("雨天低接单意愿", html)

    def test_dispatch_v7_payload_wraps_report_with_v7_story(self):
        from web_agent_demo import server_dispatch_v7

        with mock.patch.object(server_dispatch_v7, "run_case_agent", return_value=self._sample_report()):
            payload = server_dispatch_v7.build_dispatch_payload_v7("large_seed301", budget_s=10.0)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["story"]["version"], "v7-target-polish-command-center")
        self.assertEqual(payload["story"]["case_id"], "large_seed301")
        self.assertNotIn("path", payload["story"])


if __name__ == "__main__":
    unittest.main()
