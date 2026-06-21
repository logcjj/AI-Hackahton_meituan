from __future__ import annotations

import unittest
from unittest import mock


class DispatchStoryV2Test(unittest.TestCase):
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

    def test_story_v2_exposes_business_narrative_sections(self):
        from web_agent_demo.dispatch_story_v2 import build_dispatch_story_v2

        story = build_dispatch_story_v2(self._sample_report())

        self.assertEqual(story["case_id"], "large_seed301")
        self.assertEqual(story["headline"], "AutoSolver 即时履约 Agent 作战沙盘")
        self.assertIn("scene_profile", story)
        self.assertIn("kpis_initial", story)
        self.assertIn("kpis_final", story)
        self.assertIn("map_layers", story)
        self.assertIn("strategy_timeline", story)
        self.assertIn("decision_cards", story)
        self.assertIn("baseline_compare", story)
        self.assertIn("business_value", story)
        self.assertEqual(story["data_boundary"]["claim"], "脱敏业务场景沙盘")

    def test_story_v2_computes_cost_reduction_and_coverage(self):
        from web_agent_demo.dispatch_story_v2 import build_dispatch_story_v2

        story = build_dispatch_story_v2(self._sample_report())
        final = {item["id"]: item for item in story["kpis_final"]}

        self.assertEqual(final["fulfillment"]["value"], "100.0%")
        self.assertEqual(final["cost_reduction"]["value"], "68.7%")
        self.assertEqual(final["best_cost"]["value"], "657.10")
        self.assertEqual(story["baseline_compare"]["greedy"]["cost"], 2097.657539)
        self.assertAlmostEqual(story["baseline_compare"]["improvement_pct"], 68.67439, places=5)
        self.assertIn("日订单量", story["business_value"]["formula"])

    def test_story_v2_map_layers_have_semantic_nodes_and_edges(self):
        from web_agent_demo.dispatch_story_v2 import build_dispatch_story_v2

        story_a = build_dispatch_story_v2(self._sample_report())
        story_b = build_dispatch_story_v2(self._sample_report())

        self.assertEqual(story_a["map_layers"], story_b["map_layers"])
        node_types = {node["type"] for node in story_a["map_layers"]["nodes"]}
        edge_types = {edge["type"] for edge in story_a["map_layers"]["edges"]}
        self.assertTrue({"merchant_group", "courier", "risk_zone"}.issubset(node_types))
        self.assertIn("candidate", edge_types)
        self.assertIn("accepted", edge_types)
        self.assertGreaterEqual(len(story_a["map_layers"]["nodes"]), 18)
        self.assertGreaterEqual(len(story_a["map_layers"]["edges"]), 12)

    def test_story_v2_decision_cards_explain_multipdispatch_and_fields(self):
        from web_agent_demo.dispatch_story_v2 import build_dispatch_story_v2

        story = build_dispatch_story_v2(self._sample_report())
        first = story["decision_cards"][0]

        self.assertIn("多派候选", " ".join(first["rationale"]))
        self.assertIn("willingness", first["field_evidence"])
        self.assertIn("score", first["field_evidence"])
        self.assertIn("expected_cost", first["field_evidence"])
        self.assertIn("地图坐标", story["data_boundary"]["demo_fields"])

    def test_dispatch_v2_page_contains_polished_command_center(self):
        from web_agent_demo.server_dispatch_v2 import render_dispatch_index_v2

        html = render_dispatch_index_v2()

        self.assertIn("id=\"hero-metrics\"", html)
        self.assertIn("id=\"map-canvas\"", html)
        self.assertIn("id=\"strategy-timeline\"", html)
        self.assertIn("id=\"decision-stack\"", html)
        self.assertIn("id=\"boundary-strip\"", html)
        self.assertIn("AutoSolver 即时履约 Agent 作战沙盘", html)
        self.assertIn("脱敏业务场景沙盘", html)
        self.assertIn("linear-gradient", html)
        self.assertIn("首屏默认展示", html)

    def test_dispatch_v2_payload_wraps_report_with_v2_story(self):
        from web_agent_demo import server_dispatch_v2

        with mock.patch.object(server_dispatch_v2, "run_case_agent", return_value=self._sample_report()):
            payload = server_dispatch_v2.build_dispatch_payload_v2("large_seed301", budget_s=10.0)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["report"]["case_id"], "large_seed301")
        self.assertEqual(payload["story"]["case_id"], "large_seed301")
        self.assertEqual(payload["story"]["headline"], "AutoSolver 即时履约 Agent 作战沙盘")
        self.assertNotIn("path", payload["story"])


if __name__ == "__main__":
    unittest.main()
