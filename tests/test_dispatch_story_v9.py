from __future__ import annotations

import unittest
from unittest import mock


class DispatchStoryV9Test(unittest.TestCase):
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

    def test_story_v9_adds_target_density_and_layout_audit(self):
        from web_agent_demo.dispatch_story_v9 import build_dispatch_story_v9

        story = build_dispatch_story_v9(self._sample_report())

        self.assertEqual(story["version"], "v9-target-density-interaction-command-center")
        self.assertEqual(story["target_density_audit"]["left_scene_cards"], 5)
        self.assertEqual(story["target_density_audit"]["top_kpis"], 6)
        self.assertEqual(story["target_density_audit"]["right_decision_blocks"], 5)
        self.assertEqual(story["target_density_audit"]["bottom_proof_blocks"], 5)
        self.assertIn("目标图组件密度", story["target_density_audit"]["intent"])
        self.assertNotIn("Self-Evolving Code Loop", str(story))
        self.assertNotIn("雨天低接单意愿", str(story))

    def test_story_v9_models_pitch_mode_and_decision_lens(self):
        from web_agent_demo.dispatch_story_v9 import build_dispatch_story_v9

        story = build_dispatch_story_v9(self._sample_report())

        self.assertEqual(len(story["pitch_mode_tabs"]), 4)
        self.assertEqual([item["id"] for item in story["pitch_mode_tabs"]], ["scene", "decision", "baseline", "business"])
        self.assertIn("AI 自动判断", story["pitch_mode_tabs"][0]["line"])
        self.assertEqual(len(story["decision_lens"]), 5)
        self.assertIn("多派候选", story["decision_lens"][1]["value"])
        self.assertIn("贪心", str(story["decision_lens"]))
        self.assertIn("¥", str(story["decision_lens"]))

    def test_story_v9_maps_each_judge_dimension_to_visible_zone(self):
        from web_agent_demo.dispatch_story_v9 import build_dispatch_story_v9

        story = build_dispatch_story_v9(self._sample_report())

        dimensions = [item["dimension"] for item in story["judge_zone_map"]]
        self.assertEqual(dimensions, ["创新性", "完整性", "应用效果", "商业价值"])
        self.assertTrue(all(item["zone"] for item in story["judge_zone_map"]))
        self.assertTrue(all(item["visible_proof"] for item in story["judge_zone_map"]))
        self.assertIn("中央地图", str(story["judge_zone_map"]))
        self.assertIn("底部证据 dock", str(story["judge_zone_map"]))

    def test_dispatch_v9_page_has_target_density_and_interaction_hooks(self):
        from web_agent_demo.server_dispatch_v9 import render_dispatch_index_v9

        html = render_dispatch_index_v9()

        self.assertIn("v9-density-shell", html)
        self.assertIn("function renderV9SceneMeters", html)
        self.assertIn("function renderV9DecisionLens", html)
        self.assertIn("function renderV9ProofDock", html)
        self.assertIn("function renderV9ModeTabs", html)
        self.assertIn("function renderV9MapToolbar", html)
        self.assertIn("data-testid=\"v9-left-card-meter\"", html)
        self.assertIn("data-testid=\"v9-decision-lens\"", html)
        self.assertIn("data-testid=\"v9-proof-dock\"", html)
        self.assertIn("data-testid=\"v9-mode-tabs\"", html)
        self.assertIn("data-testid=\"v9-map-toolbar\"", html)
        self.assertIn("class=\"v9-meter-bar\"", html)
        self.assertIn("class=\"v9-proof-chip\"", html)
        self.assertNotIn("Self-Evolving Code Loop", html)
        self.assertNotIn("雨天低接单意愿", html)

    def test_dispatch_v9_payload_wraps_report_with_v9_story(self):
        from web_agent_demo import server_dispatch_v9

        with mock.patch.object(server_dispatch_v9, "run_case_agent", return_value=self._sample_report()):
            payload = server_dispatch_v9.build_dispatch_payload_v9("large_seed301", budget_s=10.0)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["story"]["version"], "v9-target-density-interaction-command-center")
        self.assertEqual(payload["story"]["case_id"], "large_seed301")
        self.assertNotIn("path", payload["story"])


if __name__ == "__main__":
    unittest.main()
