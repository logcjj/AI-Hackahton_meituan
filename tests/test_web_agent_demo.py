from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest import mock


class WebAgentDemoTest(unittest.TestCase):
    def test_home_page_contains_agent_system_shell(self):
        from web_agent_demo.server import render_index

        html = render_index()

        self.assertIn("AutoSolver Agent", html)
        self.assertIn("Real-time Dispatch Assignment Optimization", html)
        self.assertIn("Relative Improvement vs Greedy", html)
        self.assertIn("large_seed301", html)
        self.assertIn("00:00:08", html)
        self.assertIn("$657.10", html)
        self.assertIn("+68.7%", html)
        self.assertIn("id=\"run-agent\"", html)
        self.assertIn("运行派单推理", html)
        self.assertIn("选择调度场景", html)
        self.assertIn("data-case=\"large_seed301\"", html)
        self.assertIn("data-case=\"medium_seed201\"", html)
        self.assertIn("data-case=\"scarce_couriers_seed401\"", html)
        self.assertIn("data-case=\"low_willingness_seed501\"", html)
        self.assertIn("data-map-action=\"routes\"", html)
        self.assertIn("data-map-action=\"locate\"", html)
        self.assertIn("data-map-action=\"fit\"", html)
        self.assertIn("id=\"zoom-in\"", html)
        self.assertIn("id=\"expand-graph\"", html)
        self.assertIn("AI Reasoning Graph", html)
        self.assertIn("Input Orders", html)
        self.assertIn("Scene Diagnosis", html)
        self.assertIn("Candidate Strategy Generation", html)
        self.assertIn("Dispatch Feasibility Check", html)
        self.assertIn("Cost / Risk Critic", html)
        self.assertIn("Final Dispatch Plan (Selected)", html)
        self.assertIn("Bundle-first", html)
        self.assertIn("Multi-dispatch", html)
        self.assertIn("Repair search", html)
        self.assertIn("Greedy baseline", html)
        self.assertIn("Time-window balancing", html)
        self.assertIn('data-branch="S1"', html)
        self.assertIn("selectedBranchForReport", html)
        self.assertIn("renderStrategyCards", html)
        self.assertNotIn('class="strategy best"', html)
        self.assertNotIn("S1 ✓</h4>", html)
        self.assertIn("Live Dispatch Assignment Map", html)
        self.assertIn("调度片区", html)
        self.assertIn("订单组", html)
        self.assertIn("订单", html)
        self.assertIn("骑手", html)
        self.assertIn("最终派单连线", html)
        self.assertIn("被淘汰候选", html)
        self.assertIn("骑手位置", html)
        self.assertIn("leaflet.css", html)
        self.assertIn("leaflet.js", html)
        self.assertIn("id=\"real-map\"", html)
        self.assertIn("basemaps.cartocdn.com/dark_nolabels", html)
        self.assertIn("pointToLatLng", html)
        self.assertIn("renderLeafletDispatchMap", html)
        self.assertIn("return false;", html)
        self.assertIn("map-entities", html)
        self.assertIn("pickup-leg", html)
        self.assertIn("dispatchArrowFor", html)
        self.assertIn("dispatch-arrow", html)
        self.assertIn("等待运行派单推理", html)
        for fake_value in ["C017 + C035", "Merchant R02", "<span class=\"chip\">T0012</span>", "T0018<small>", "T0023<small>"]:
            self.assertNotIn(fake_value, html)
        self.assertNotIn("selected-route", html)
        self.assertNotIn("candidate-route", html)
        self.assertIn("Decision Explanation", html)
        self.assertIn("Selected Dispatch Assignment", html)
        self.assertIn("骑手接单概率", html)
        self.assertIn("Compared to Greedy", html)
        self.assertIn("Candidate Dispatch Strategy Comparison", html)
        self.assertIn("Final AutoSolver", html)
        self.assertIn("(Selected)", html)
        self.assertIn("Best trade-off across cost/risk/ETA", html)
        self.assertIn("map-bg", html)
        self.assertIn("district", html)
        self.assertIn("anonymous-navigation-layer", html)
        self.assertIn("simulated-map-layer", html)
        self.assertIn("renderSimulatedBaseMap", html)
        self.assertIn("building-block", html)
        self.assertIn("traffic-band", html)
        self.assertIn("commerce-hotspot", html)
        self.assertIn("assignments:", html)
        self.assertIn("assignmentForEntity", html)
        self.assertIn("sceneLabels", html)
        self.assertIn("caseCatalog", html)
        self.assertIn("profileForCase", html)
        self.assertIn("renderAssignmentDetail", html)
        self.assertIn("updateReasonSummary", html)
        self.assertIn("label.dataset.assignment", html)
        self.assertIn("dispatch-link", html)
        self.assertIn("courier-node", html)
        self.assertIn("function applyMapFocus", html)
        self.assertIn("function labelOffsetFor", html)
        self.assertIn("function simulationPreviewMap", html)
        self.assertIn("function simulationFinalMap", html)
        self.assertIn("function renderEntityPreviewDetail", html)
        self.assertIn("function runCurrentSimulationSample", html)
        self.assertIn("function applySimulationSample", html)
        self.assertIn("function refreshSimulationSample", html)
        self.assertIn("/api/simulation-sample?", html)
        self.assertIn("sample-preview", html)
        self.assertIn("hideLabel: true", html)
        self.assertIn('assignments: []', html)
        self.assertIn("focus-selected", html)
        self.assertIn("data-selected-assignment", html)
        self.assertIn('pin.classList.toggle("active-assignment"', html)
        self.assertIn('dispatchArrowFor(orderPoints.length ? deliveryRoute : pickupRoute, arrowCls, assignment.id, isActive)', html)
        self.assertIn('event.target.closest(".map-label, .pin, .dispatch-link, .dispatch-arrow")', html)
        self.assertIn("const isActive = assignment.id === selectedAssignment;", html)
        self.assertIn("stroke: rgba(156, 177, 192, .44)", html)
        self.assertIn("L${midX.toFixed(1)}", html)
        self.assertNotIn('const cls = index === 0 ? "dispatch-link primary"', html)
        for forbidden in ["Proxy score", "local_cost", "40/40", "本地分数", "本地评分", "官方成绩"]:
            self.assertNotIn(forbidden, html)

    def test_dispatch_map_uses_case_candidate_data(self):
        from web_agent_demo.server import build_dispatch_assignment_map

        payload = build_dispatch_assignment_map("scarce_couriers_seed401")

        self.assertEqual(payload["stage"], "preview")
        self.assertGreater(len(payload["assignments"]), 0)
        self.assertGreater(len(payload["entities"]), 0)
        first = payload["assignments"][0]
        self.assertRegex(first["task_key"], r"^T\d+")
        self.assertRegex(first["courier"], r"^C\d+")
        self.assertTrue(str(first["pickup"]).startswith("G"))
        entity_by_id = {item["id"]: item for item in payload["entities"]}
        self.assertGreaterEqual(entity_by_id[first["pickup"]]["x"], 7.5)
        self.assertLessEqual(entity_by_id[first["pickup"]]["x"], 92.5)
        self.assertIn(str(first["courier"]).split(" + ")[0], entity_by_id)
        self.assertTrue(all(order in entity_by_id for order in first["map_orders"]))

    def test_all_listed_cases_have_dispatch_maps(self):
        from web_agent_demo.server import build_dispatch_assignment_map, list_cases

        seen_first_assignments = set()
        for case in list_cases():
            payload = build_dispatch_assignment_map(case["id"])
            self.assertEqual(payload["case_id"], case["id"])
            self.assertGreater(len(payload["assignments"]), 0, case["id"])
            self.assertGreater(len(payload["entities"]), 0, case["id"])
            first = payload["assignments"][0]
            seen_first_assignments.add((first["task_key"], first["courier"]))
            entity_by_id = {item["id"]: item for item in payload["entities"]}
            self.assertIn(first["pickup"], entity_by_id)
            for courier in str(first["courier"]).split(" + "):
                self.assertIn(courier, entity_by_id)
            for order in first["map_orders"]:
                self.assertIn(order, entity_by_id)

        self.assertGreater(len(seen_first_assignments), 5)

    def test_dispatch_map_uses_network_clusters_not_lanes(self):
        from web_agent_demo.server import build_dispatch_assignment_map

        payload = build_dispatch_assignment_map("large_seed301", limit=8)
        pickups = [
            entity
            for entity in payload["entities"]
            if entity["kind"] == "pickup_cluster"
        ]
        xs = [entity["x"] for entity in pickups]
        ys = [entity["y"] for entity in pickups]

        self.assertGreaterEqual(len(pickups), 6)
        self.assertGreater(max(xs) - min(xs), 25)
        self.assertGreater(max(ys) - min(ys), 18)
        rounded_y_steps = {
            round(ys[index + 1] - ys[index], 1)
            for index in range(len(ys) - 1)
        }
        self.assertGreater(len(rounded_y_steps), 3)

    def test_simulated_scenarios_generate_ten_samples_each(self):
        from web_agent_demo.server import build_simulated_scenario_sample, list_simulated_scenarios

        scenarios = list_simulated_scenarios()

        self.assertGreaterEqual(len(scenarios), 5)
        self.assertTrue(all(item["sample_count"] == 10 for item in scenarios))
        self.assertTrue(all(item["map_style"] == "baidu_like_simulated" for item in scenarios))
        for scenario in scenarios:
            for sample_index in range(10):
                sample = build_simulated_scenario_sample(str(scenario["id"]), sample_index)
                self.assertEqual(sample["stage"], "preview")
                self.assertEqual(sample["sample_index"], sample_index)
                self.assertGreaterEqual(len(sample["merchants"]), 3)
                self.assertLessEqual(len(sample["merchants"]), 6)
                self.assertGreaterEqual(len(sample["couriers"]), 7)
                self.assertGreaterEqual(len(sample["candidates"]), len(sample["merchants"]) * 2)
                self.assertEqual(len(sample["assignments"]), len(sample["merchants"]))
                self.assertTrue(sample["map_layers"]["hide_road_names"])
                self.assertEqual(sample["map_layers"]["road_name_labels"], [])
                self.assertGreaterEqual(len(sample["map_layers"]["roads"]), 8)
                self.assertGreaterEqual(len(sample["map_layers"]["districts"]), 12)
                self.assertGreaterEqual(len(sample["map_layers"]["roads"]), 20)
                self.assertGreaterEqual(len(sample["map_layers"]["building_blocks"]), 20)
                self.assertGreaterEqual(len(sample["map_layers"]["commerce_hotspots"]), 3)
                self.assertGreaterEqual(len(sample["map_layers"]["intersections"]), 6)
                self.assertTrue(all(not road["name_visible"] for road in sample["map_layers"]["roads"]))
                merchant_points = [(float(item["x"]), float(item["y"])) for item in sample["merchants"]]
                courier_points = [(float(item["x"]), float(item["y"])) for item in sample["couriers"]]
                self.assertGreater(len(set(merchant_points)), 2)
                self.assertGreater(len(set(courier_points)), 5)

    def test_simulated_samples_cover_all_strategy_paths(self):
        from web_agent_demo.server import build_simulated_scenario_samples

        samples = build_simulated_scenario_samples()
        selected = {sample["selected_strategy_id"] for sample in samples}

        self.assertEqual(len(samples), 60)
        self.assertTrue({"S1", "S2", "S3", "S4", "S5"}.issubset(selected))
        for sample in samples:
            path = sample["strategy_path"]
            self.assertEqual(len(path), 5)
            self.assertEqual(sum(1 for item in path if item["status"] == "selected"), 1)
            for assignment in sample["assignments"]:
                self.assertIn("merchant_id", assignment)
                self.assertIn("courier_id", assignment)
                self.assertIn("backup_courier_id", assignment)
                self.assertGreater(float(assignment["cost"]), 0)
                self.assertGreaterEqual(int(assignment["eta_min"]), 6)
                self.assertIn(assignment["risk"], {"Low", "Medium", "High"})

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

        self.assertNotIn("evolution-step-generate", html)
        self.assertNotIn("data-evolution-step", html)
        self.assertNotIn("function paintEvolutionPanel()", html)
        self.assertIn("evolution_generate", html)
        self.assertIn("evolution_validate", html)
        self.assertIn("evolution_trial", html)
        self.assertIn("handleProgressEvent", html)

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
