from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest import mock


class WebAgentDemoTest(unittest.TestCase):
    def test_home_page_contains_agent_system_shell(self):
        from web_agent_demo.server import render_index

        html = render_index()

        self.assertIn("AutoSolver Agent System", html)
        self.assertIn(">AutoSolver Agent Workbench</h1>", html)
        self.assertNotIn("看见 Agent 如何一步步求解", html)
        self.assertNotIn("AGENT LOOP", html)
        self.assertIn("id=\"run-agent\"", html)
        self.assertIn("Developer Workbench", html)
        self.assertIn("场景摘要", html)
        self.assertIn("id=\"scenario-name\"", html)
        self.assertIn("id=\"scenario-risk-tags\"", html)
        self.assertIn("Baseline vs AutoSolver", html)
        self.assertIn("id=\"result-comparison\"", html)
        self.assertIn("运行调度分析", html)
        self.assertIn("调度场景", html)
        self.assertIn("Agent 阶段", html)
        self.assertIn("Planner", html)
        self.assertIn("Executor", html)
        self.assertIn("Critic", html)
        self.assertIn("Controller", html)
        self.assertIn("Memory", html)
        self.assertIn("Evolution", html)
        self.assertIn("Evolution Memory", html)
        self.assertIn("Self-Evolving Code Loop", html)
        self.assertIn("Generate", html)
        self.assertIn("Safety Gate", html)
        self.assertIn("Sandbox Execute", html)
        self.assertIn("Rollback", html)
        self.assertIn("Evolution Memory", html)
        self.assertIn(".timeline-panel, .inspector { min-height: 877px; }", html)
        self.assertIn(".timeline-panel, .inspector { min-height: 0; }", html)
        self.assertIn("min-height: 156px", html)
        self.assertIn("\n      height: 620px;", html)
        self.assertIn(".timeline { height: 460px; }", html)
        self.assertNotIn("grid-template-rows: auto auto minmax(0, 1fr)", html)
        self.assertIn("生成策略变体", html)
        self.assertIn("case 画像", html)
        self.assertIn("相似样例检索", html)
        self.assertIn("审计与候选池", html)
        self.assertIn("只有 accepted/candidate/trusted/promoted 策略才会被后续相似样例 replay", html)
        for forbidden in ["Proxy score", "local_cost", "40/40", "本地分数", "本地评分", "官方成绩"]:
            self.assertNotIn(forbidden, html)

    def test_home_page_keeps_review_alignment_out_of_frontend_layout(self):
        from web_agent_demo.server import render_index

        html = render_index()

        self.assertNotIn('id="official-alignment"', html)
        self.assertNotIn('id="official-rubric"', html)
        self.assertNotIn('id="official-agent-requirements"', html)
        self.assertNotIn('id="official-run-evidence"', html)
        self.assertNotIn('id="review-alignment"', html)
        self.assertNotIn("官方要求对齐", html)
        self.assertNotIn("Video + Audio Evidence", html)
        self.assertNotIn("不是只交一个求解器", html)

    def test_evolution_loop_uses_dynamic_replay_panel(self):
        from web_agent_demo.server import render_index

        html = render_index()

        for step_id in [
            "evolution-step-generate",
            "evolution-step-recall",
            "evolution-step-safety",
            "evolution-step-sandbox",
            "evolution-step-decision",
            "evolution-step-memory",
        ]:
            self.assertIn(f'id="{step_id}"', html)
        self.assertIn("data-evolution-step", html)
        self.assertIn("pending", html)
        self.assertIn("let evolutionState", html)
        self.assertIn("function paintEvolutionPanel()", html)
        self.assertIn("未命中相似候选，本轮仅生成新策略变体", html)
        self.assertIn("仅写入审计日志，不进入候选池", html)
        self.assertIn("失败原因", html)
        self.assertIn("系统动作", html)
        self.assertIn("试跑超时", html)
        self.assertIn("质量门未通过", html)

    def test_case_listing_exposes_large_seed301_without_local_paths(self):
        from web_agent_demo.server import list_cases

        cases = list_cases()

        self.assertTrue(any(case["id"] == "large_seed301" for case in cases))
        self.assertTrue(all("path" not in case for case in cases))
        self.assertTrue(all("scenario_name" in case for case in cases))
        self.assertTrue(all("scenario_type" in case for case in cases))
        self.assertTrue(all("risk_tags" in case for case in cases))
        self.assertTrue(all("operator_note" in case for case in cases))
        self.assertTrue(all("source_type" in case for case in cases))
        large_case = next(case for case in cases if case["id"] == "large_seed301")
        self.assertEqual(large_case["scenario_name"], "官方大规模候选调度")
        self.assertEqual(large_case["source_type"], "official_case")
        self.assertIn("候选行多", large_case["risk_tags"])

    def test_blueprint_exposes_agent_capabilities(self):
        from autosolver_agent.system import get_agent_blueprint

        blueprint = get_agent_blueprint()

        self.assertIn("objective", blueprint)
        self.assertIn("review_alignment", blueprint)
        self.assertGreaterEqual(len(blueprint["capabilities"]), 4)
        self.assertTrue(any(item["id"] == "critic" for item in blueprint["capabilities"]))
        self.assertTrue(any(item["id"] == "self_evolution" for item in blueprint["capabilities"]))
        self.assertTrue(any(item["id"] == "production_solver" for item in blueprint["strategy_catalog"]))
        alignment = blueprint["review_alignment"]
        self.assertEqual(alignment["source"]["type"], "competition_delivery_requirements")
        self.assertIn("solution_quality", alignment["review_dimensions"])
        self.assertIn("autonomous_iteration", alignment["review_dimensions"])
        self.assertIn("technical_report", alignment["review_dimensions"])
        self.assertEqual(len(alignment["agent_requirements"]), 4)

    def test_api_payload_uses_agent_controller(self):
        from web_agent_demo import server

        fake_report = {
            "case_id": "large_seed301",
            "regime": "large",
            "status": "ok",
            "wall_time_s": 1.23,
            "features": {"tasks": 40, "couriers": 80, "rows": 1234},
            "best": {
                "strategy": "production_solver",
                "local_cost": 657.1,
                "valid": True,
                "covered_tasks": 40,
                "total_tasks": 40,
                "groups": 40,
                "used_couriers": 40,
                "uncovered_tasks": [],
            },
            "rounds": [
                {
                    "round": 1,
                    "reason": "initial diverse exploration",
                    "strategies": [
                        {
                            "name": "greedy_baseline",
                            "local_cost": 700.0,
                            "accepted": True,
                            "elapsed_ms": 10.0,
                            "valid": True,
                            "covered_tasks": 40,
                            "total_tasks": 40,
                        }
                    ],
                }
            ],
            "events": [{"type": "attempt_result", "strategy": "greedy_baseline", "accepted": True}],
            "solution": [("T0000", ["C000"])],
        }

        with mock.patch.object(server, "run_case_agent", return_value=fake_report):
            payload = server.build_agent_payload("large_seed301", budget_s=10.0)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["report"]["best"]["strategy"], "production_solver")
        self.assertEqual(json.loads(json.dumps(payload))["status"], "ok")

    def test_agent_stream_uses_live_observer_contract(self):
        from autosolver_agent import system

        seen = []

        def observer(event):
            seen.append(event["type"])

        fake_module = mock.Mock()
        fake_module._solution_expected_cost.return_value = 1.0
        fake_module._fallback_official_greedy.return_value = []
        fake_module._solve_single_task_multidispatch.return_value = []
        fake_module._solve_disjoint_then_multidispatch.return_value = []
        fake_module._solve_pair_potential_matching.return_value = []
        fake_module._solve_sparse_cover.return_value = []
        fake_module._solve_low_global_column_search.return_value = []
        fake_module._solve_low_column_search.return_value = []
        fake_module._solve_scarce_k2_column_search.return_value = []
        fake_module._solve_scarce_bundle_mcf_enum.return_value = []
        fake_module.solve.return_value = []
        fake_evolution = mock.Mock()
        fake_evolution.memory_path = "mock-evolution-memory.jsonl"
        fake_evolution.registry_path = "mock-strategy-registry.json"
        fake_evolution.trusted_strategies.return_value = []
        fake_evolution.generate_strategy.return_value = SimpleNamespace(strategy_id="gen_test_v001", path="gen_test_v001.py")
        fake_evolution.safety_check.return_value = SimpleNamespace(passed=False, reason="mock safety gate")

        with mock.patch.object(system, "load_solver", return_value=fake_module), mock.patch.object(system, "parse_candidates", return_value=([("T0000", ("T0000",), "C000", 1.0, 0.9, 0)], {"T0000"})), mock.patch.object(system, "infer_regime", return_value="large"), mock.patch.object(system, "EvolutionManager", return_value=fake_evolution), mock.patch.object(system, "summarize_solution", return_value={"valid": True, "covered_tasks": 1, "total_tasks": 1, "groups": 0, "used_couriers": 0, "uncovered_tasks": [], "riders_per_group": {}, "tasks_per_group": {}, "invalid_reasons": []}):
            report = system.run_agent("task_id_list\nT0000\tC000\t1\t0.9\n", budget_s=1.0, observer=observer)

        self.assertEqual(report["status"], "ok")
        self.assertIn("perception", seen)
        self.assertIn("evolution_generate", seen)
        self.assertIn("evolution_validate", seen)
        self.assertIn("final", seen)
        self.assertTrue(any(item in seen for item in ["attempt_result", "best_update"]))


if __name__ == "__main__":
    unittest.main()
