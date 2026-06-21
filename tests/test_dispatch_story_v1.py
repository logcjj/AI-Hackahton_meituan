from __future__ import annotations

import unittest
from unittest import mock


class DispatchStoryV1Test(unittest.TestCase):
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
                {"type": "best_update", "strategy": "production_solver"},
            ],
            "evolution": {"mode": "experimental-track-no-solver-mutation"},
        }

    def test_build_story_separates_real_and_demo_fields(self):
        from web_agent_demo.dispatch_story_v1 import build_dispatch_story

        story = build_dispatch_story(self._sample_report())

        self.assertEqual(story["case_id"], "large_seed301")
        self.assertEqual(story["data_boundary"]["real_fields"][0], "任务/骑手/候选行")
        self.assertIn("地图坐标", story["data_boundary"]["demo_fields"])
        self.assertIn("商业金额换算", story["data_boundary"]["demo_fields"])
        self.assertEqual(story["data_boundary"]["claim"], "脱敏业务场景沙盘")

    def test_build_story_computes_baseline_delta_and_kpis(self):
        from web_agent_demo.dispatch_story_v1 import build_dispatch_story

        story = build_dispatch_story(self._sample_report())
        kpis = {item["id"]: item for item in story["kpis"]}

        self.assertEqual(kpis["fulfillment"]["value"], "100.0%")
        self.assertEqual(kpis["orders"]["value"], "40")
        self.assertEqual(kpis["couriers"]["value"], "80")
        self.assertEqual(kpis["expected_cost"]["value"], "657.10")
        self.assertEqual(kpis["cost_reduction"]["value"], "68.7%")
        self.assertEqual(story["baseline"]["strategy"], "greedy_baseline")
        self.assertEqual(story["baseline"]["cost"], 2097.657539)
        self.assertAlmostEqual(story["baseline"]["delta_pct"], 68.67439, places=5)

    def test_build_story_creates_stable_map_nodes_and_edges(self):
        from web_agent_demo.dispatch_story_v1 import build_dispatch_story

        story_a = build_dispatch_story(self._sample_report())
        story_b = build_dispatch_story(self._sample_report())

        self.assertEqual(story_a["map"]["nodes"], story_b["map"]["nodes"])
        self.assertEqual(story_a["map"]["edges"], story_b["map"]["edges"])
        self.assertGreaterEqual(len(story_a["map"]["nodes"]), 10)
        self.assertGreaterEqual(len(story_a["map"]["edges"]), 8)
        node_types = {node["type"] for node in story_a["map"]["nodes"]}
        self.assertTrue({"merchant", "courier", "scene"}.issubset(node_types))
        edge_kinds = {edge["kind"] for edge in story_a["map"]["edges"]}
        self.assertIn("accepted-dispatch", edge_kinds)
        self.assertIn("candidate-dispatch", edge_kinds)

    def test_decision_explanations_make_multipdispatch_explicit(self):
        from web_agent_demo.dispatch_story_v1 import build_dispatch_story

        story = build_dispatch_story(self._sample_report())
        first = story["decisions"][0]

        self.assertIn("任务组", first["title"])
        self.assertIn("多派候选", first["bullets"][0])
        self.assertIn("willingness", first["metrics"])
        self.assertIn("score", first["metrics"])
        self.assertIn("expected_cost", first["metrics"])

    def test_dispatch_page_contains_command_center_shell(self):
        from web_agent_demo.server_dispatch_v1 import render_dispatch_index

        html = render_dispatch_index()

        self.assertIn("即时履约智能调度指挥舱", html)
        self.assertIn("id=\"dispatch-map\"", html)
        self.assertIn("id=\"data-boundary\"", html)
        self.assertIn("Baseline vs AutoSolver", html)
        self.assertIn("商业价值 ROI 模拟器", html)
        self.assertIn("开始推理", html)
        self.assertIn("脱敏业务场景沙盘", html)
        self.assertIn("地图坐标为演示映射", html)
        self.assertIn(".node-label { fill: var(--text); font-size: 2.2px;", html)

    def test_dispatch_payload_wraps_report_with_story(self):
        from web_agent_demo import server_dispatch_v1

        with mock.patch.object(server_dispatch_v1, "run_case_agent", return_value=self._sample_report()):
            payload = server_dispatch_v1.build_dispatch_payload("large_seed301", budget_s=10.0)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["report"]["case_id"], "large_seed301")
        self.assertEqual(payload["story"]["case_id"], "large_seed301")
        self.assertEqual(payload["story"]["headline"], "即时履约智能调度指挥舱")
        self.assertNotIn("path", payload["story"])


if __name__ == "__main__":
    unittest.main()
