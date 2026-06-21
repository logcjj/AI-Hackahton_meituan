from __future__ import annotations

import unittest
from unittest import mock


class DispatchStoryV4Test(unittest.TestCase):
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

    def test_story_v4_extends_v3_with_review_and_meeting_alignment(self):
        from web_agent_demo.dispatch_story_v4 import build_dispatch_story_v4

        story = build_dispatch_story_v4(self._sample_report())

        self.assertEqual(story["headline"], "AutoSolver Agent 即时履约智能调度指挥舱")
        self.assertEqual(story["ai_scene_judgement"]["mode"], "AI_AUTO_INFERRED")
        self.assertIn("review_alignment", story)
        self.assertIn("meeting_takeaways", story)
        self.assertEqual(len(story["review_alignment"]), 4)
        self.assertIn("创新性", {item["dimension"] for item in story["review_alignment"]})
        self.assertIn("完整性", {item["dimension"] for item in story["review_alignment"]})
        self.assertIn("应用效果", {item["dimension"] for item in story["review_alignment"]})
        self.assertIn("商业价值", {item["dimension"] for item in story["review_alignment"]})

    def test_story_v4_preserves_core_metrics_and_target_semantics(self):
        from web_agent_demo.dispatch_story_v4 import build_dispatch_story_v4

        story = build_dispatch_story_v4(self._sample_report())
        metrics = {item["id"]: item for item in story["metric_strip"]}

        self.assertEqual(metrics["completion_rate"]["value"], "100.0%")
        self.assertEqual(metrics["unassigned_orders"]["value"], "0 单")
        self.assertEqual(metrics["relative_improvement"]["value"], "+68.7%")
        self.assertEqual(story["baseline_table"]["rows"][0]["autosolver"], "100.0%")
        self.assertGreaterEqual(len(story["operation_map"]["nodes"]), 26)
        self.assertGreaterEqual(len(story["operation_map"]["edges"]), 22)
        self.assertIn("多派候选", story["decision_panel"]["decision_reason"][0])

    def test_story_v4_keeps_cancelled_modules_out(self):
        from web_agent_demo.dispatch_story_v4 import build_dispatch_story_v4

        story = build_dispatch_story_v4(self._sample_report())
        dumped = str(story)

        self.assertNotIn("雨天低接单意愿", dumped)
        self.assertNotIn("Self-Evolving Code Loop", dumped)
        self.assertIn("策略记忆库", story["strategy_memory"]["title"])
        self.assertIn("AI 场景识别", story["ai_scene_judgement"]["title"])

    def test_dispatch_v4_page_is_fixed_stage_target_dashboard(self):
        from web_agent_demo.server_dispatch_v4 import render_dispatch_index_v4

        html = render_dispatch_index_v4()

        self.assertIn("--stage-width: 1920px", html)
        self.assertIn("--stage-height: 1080px", html)
        self.assertIn("presentation-scale", html)
        self.assertIn("target-dashboard", html)
        self.assertIn("id=\"top-kpi-strip\"", html)
        self.assertIn("id=\"left-scene-rail\"", html)
        self.assertIn("id=\"map-stage\"", html)
        self.assertIn("id=\"right-decision-panel\"", html)
        self.assertIn("id=\"review-alignment\"", html)
        self.assertIn("创新性", html)
        self.assertIn("完整性", html)
        self.assertIn("应用效果", html)
        self.assertIn("商业价值", html)
        self.assertNotIn("Self-Evolving Code Loop", html)
        self.assertNotIn("雨天低接单意愿", html)

    def test_dispatch_v4_payload_wraps_report_with_v4_story(self):
        from web_agent_demo import server_dispatch_v4

        with mock.patch.object(server_dispatch_v4, "run_case_agent", return_value=self._sample_report()):
            payload = server_dispatch_v4.build_dispatch_payload_v4("large_seed301", budget_s=10.0)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["story"]["case_id"], "large_seed301")
        self.assertEqual(payload["story"]["headline"], "AutoSolver Agent 即时履约智能调度指挥舱")
        self.assertNotIn("path", payload["story"])


if __name__ == "__main__":
    unittest.main()
