from __future__ import annotations

import unittest
from unittest import mock


class DispatchStoryV3Test(unittest.TestCase):
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

    def test_story_v3_matches_meeting_driven_command_center_sections(self):
        from web_agent_demo.dispatch_story_v3 import build_dispatch_story_v3

        story = build_dispatch_story_v3(self._sample_report())

        self.assertEqual(story["headline"], "AutoSolver Agent 即时履约智能调度指挥舱")
        self.assertEqual(story["ai_scene_judgement"]["mode"], "AI_AUTO_INFERRED")
        self.assertIn("command_center", story)
        self.assertIn("metric_strip", story)
        self.assertIn("operation_map", story)
        self.assertIn("decision_panel", story)
        self.assertIn("agent_workflow", story)
        self.assertIn("plan_evaluation", story)
        self.assertIn("baseline_table", story)
        self.assertIn("strategy_memory", story)
        self.assertIn("commercial_roi", story)

    def test_story_v3_removes_cancelled_target_modules(self):
        from web_agent_demo.dispatch_story_v3 import build_dispatch_story_v3

        story = build_dispatch_story_v3(self._sample_report())
        dumped = str(story)

        self.assertIn("右上固定雨天接单意愿卡", story["removed_modules"])
        self.assertIn("左下自进化与安全回退大模块", story["removed_modules"])
        self.assertNotIn("雨天低接单意愿", dumped)
        self.assertNotIn("Self-Evolving Code Loop", dumped)
        self.assertIn("策略记忆库", story["strategy_memory"]["title"])

    def test_story_v3_keeps_real_metrics_and_baseline_comparison(self):
        from web_agent_demo.dispatch_story_v3 import build_dispatch_story_v3

        story = build_dispatch_story_v3(self._sample_report())
        metrics = {item["id"]: item for item in story["metric_strip"]}

        self.assertEqual(metrics["completion_rate"]["value"], "100.0%")
        self.assertEqual(metrics["unassigned_orders"]["value"], "0 单")
        self.assertEqual(metrics["cost_index"]["value"], "91.3")
        self.assertEqual(metrics["rider_usage"]["value"], "80 人")
        self.assertEqual(metrics["relative_improvement"]["value"], "+68.7%")
        self.assertEqual(story["baseline_table"]["rows"][0]["autosolver"], "100.0%")
        self.assertAlmostEqual(story["baseline_table"]["improvement_pct"], 68.67439, places=5)

    def test_story_v3_operation_map_uses_target_semantics(self):
        from web_agent_demo.dispatch_story_v3 import build_dispatch_story_v3

        story_a = build_dispatch_story_v3(self._sample_report())
        story_b = build_dispatch_story_v3(self._sample_report())

        self.assertEqual(story_a["operation_map"], story_b["operation_map"])
        node_types = {node["type"] for node in story_a["operation_map"]["nodes"]}
        edge_types = {edge["type"] for edge in story_a["operation_map"]["edges"]}
        self.assertTrue({"order_high_risk", "order_normal", "courier"}.issubset(node_types))
        self.assertIn("candidate_plan", edge_types)
        self.assertIn("allocated_plan", edge_types)
        self.assertGreaterEqual(len(story_a["operation_map"]["nodes"]), 22)
        self.assertGreaterEqual(len(story_a["operation_map"]["edges"]), 16)

    def test_story_v3_decision_panel_has_selected_couriers_and_rejected_plans(self):
        from web_agent_demo.dispatch_story_v3 import build_dispatch_story_v3

        story = build_dispatch_story_v3(self._sample_report())
        decision = story["decision_panel"]

        self.assertIn("selected_order_group", decision)
        self.assertGreaterEqual(len(decision["selected_couriers"]), 2)
        self.assertGreaterEqual(len(decision["rejected_plans"]), 2)
        self.assertIn("willingness", decision["selected_couriers"][0])
        self.assertIn("distance_km", decision["selected_couriers"][0])
        self.assertIn("多派候选", decision["decision_reason"][0])

    def test_dispatch_v3_page_looks_like_target_but_omits_cancelled_sections(self):
        from web_agent_demo.server_dispatch_v3 import render_dispatch_index_v3

        html = render_dispatch_index_v3()

        self.assertIn("AutoSolver Agent", html)
        self.assertIn("即时履约智能调度指挥舱", html)
        self.assertIn("id=\"scene-intelligence\"", html)
        self.assertIn("id=\"scenario-rail\"", html)
        self.assertIn("id=\"risk-portrait\"", html)
        self.assertIn("id=\"operation-map\"", html)
        self.assertIn("id=\"decision-panel\"", html)
        self.assertIn("id=\"workflow-strip\"", html)
        self.assertIn("id=\"plan-evaluation\"", html)
        self.assertIn("id=\"baseline-table\"", html)
        self.assertIn("id=\"strategy-memory\"", html)
        self.assertIn("id=\"commercial-roi\"", html)
        self.assertIn("mapbox-like-grid", html)
        self.assertNotIn("Self-Evolving Code Loop", html)
        self.assertNotIn("雨天低接单意愿", html)

    def test_dispatch_v3_payload_wraps_report_with_v3_story(self):
        from web_agent_demo import server_dispatch_v3

        with mock.patch.object(server_dispatch_v3, "run_case_agent", return_value=self._sample_report()):
            payload = server_dispatch_v3.build_dispatch_payload_v3("large_seed301", budget_s=10.0)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["report"]["case_id"], "large_seed301")
        self.assertEqual(payload["story"]["case_id"], "large_seed301")
        self.assertEqual(payload["story"]["headline"], "AutoSolver Agent 即时履约智能调度指挥舱")
        self.assertNotIn("path", payload["story"])


if __name__ == "__main__":
    unittest.main()
