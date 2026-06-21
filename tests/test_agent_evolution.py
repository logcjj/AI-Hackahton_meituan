from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class AgentEvolutionTest(unittest.TestCase):
    def test_blueprint_and_report_include_review_alignment_evidence(self):
        from autosolver_agent import system

        blueprint = system.get_agent_blueprint()

        self.assertIn("review_alignment", blueprint)
        alignment = blueprint["review_alignment"]
        self.assertEqual(alignment["source"]["type"], "competition_delivery_requirements")
        self.assertIn("solution_quality", alignment["review_dimensions"])
        self.assertIn("autonomous_iteration", alignment["review_dimensions"])
        self.assertIn("technical_report", alignment["review_dimensions"])
        self.assertEqual(
            [item["id"] for item in alignment["agent_requirements"]],
            ["autonomous_strategy_exploration", "automatic_evaluation_filtering", "iterative_improvement_loop", "current_best_output"],
        )
        self.assertEqual(alignment["runtime_boundary"]["per_case_budget_s"], 10)

        fake_module = mock.Mock()
        fake_module._solution_expected_cost.return_value = 1.0
        fake_module._fallback_official_greedy.return_value = [("T0000", ["C000"])]
        fake_module._solve_single_task_multidispatch.return_value = [("T0000", ["C000"])]
        fake_module._solve_disjoint_then_multidispatch.return_value = [("T0000", ["C000"])]
        fake_module._solve_pair_potential_matching.return_value = [("T0000", ["C000"])]
        fake_module._solve_sparse_cover.return_value = [("T0000", ["C000"])]
        fake_module._solve_low_global_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_low_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_scarce_k2_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_scarce_bundle_mcf_enum.return_value = [("T0000", ["C000"])]
        fake_module.solve.return_value = [("T0000", ["C000"])]

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(system, "EVOLUTION_ROOT", Path(tmp)), mock.patch.object(system, "load_solver", return_value=fake_module), mock.patch.object(system, "parse_candidates", return_value=([("T0000", ("T0000",), "C000", 1.0, 0.9, 0)], {"T0000"})), mock.patch.object(system, "infer_regime", return_value="large"), mock.patch.object(system, "summarize_solution", return_value={"valid": True, "covered_tasks": 1, "total_tasks": 1, "groups": 1, "used_couriers": 1, "uncovered_tasks": [], "riders_per_group": {}, "tasks_per_group": {}, "invalid_reasons": []}):
            report = system.run_agent("task_id_list\nT0000\tC000\t1\t0.9\n", budget_s=1.0)

        self.assertIn("review_alignment", report)
        self.assertIn("alignment_evidence", report["review_alignment"])
        evidence = report["review_alignment"]["alignment_evidence"]
        self.assertGreaterEqual(evidence["strategy_attempts"], 1)
        self.assertGreaterEqual(evidence["critic_decisions"], 1)
        self.assertTrue(evidence["has_iterative_adaptation"])
        self.assertTrue(evidence["has_self_evolution_track"])
        self.assertEqual(evidence["runtime_budget_s"], 1.0)

    def test_evolution_quality_gate_display_is_case_aware(self):
        from autosolver_agent.system import _evolution_trial_display

        low = _evolution_trial_display(
            "quality regression",
            False,
            {
                "regime": "low-willingness",
                "tasks": 30,
                "couriers": 60,
                "rows": 689,
                "avg_willingness": 0.143,
                "has_bundles": True,
            },
        )
        scarce = _evolution_trial_display(
            "quality regression",
            False,
            {
                "regime": "scarce",
                "tasks": 30,
                "couriers": 18,
                "rows": 512,
                "avg_willingness": 0.5,
                "has_bundles": True,
            },
        )

        self.assertNotEqual(low["reason_label"], scarce["reason_label"])
        self.assertIn("低意愿", low["reason_label"])
        self.assertIn("稀缺", scarce["reason_label"])
        self.assertIn("低接受率", low["reason_detail"])
        self.assertIn("骑手复用", scarce["reason_detail"])

    def test_generated_strategy_passes_safety_runs_and_updates_memory(self):
        from autosolver_agent.evolution import EvolutionManager

        with tempfile.TemporaryDirectory() as tmp:
            manager = EvolutionManager(Path(tmp))
            case_profile = {
                "regime": "low-willingness",
                "tasks": 30,
                "couriers": 60,
                "rows": 689,
                "avg_willingness": 0.21,
                "has_bundles": False,
            }
            generated = manager.generate_strategy("low-willingness", "prefer generated low column probe", case_profile)

            safety = manager.safety_check(generated.path)
            self.assertTrue(safety.passed, safety.reason)

            candidates = [("T0000", ("T0000",), "C000", 1.0, 0.9, 0)]
            all_tasks = {"T0000"}
            outcome = manager.run_generated_strategy(
                generated,
                candidates,
                all_tasks,
                deadline_s=0.2,
                helpers={"fallback_greedy": lambda rows: [("T0000", ["C000"])]},
                baseline_cost=10.0,
                score_fn=lambda solution: 1.0,
                summarize_fn=lambda solution, cost: {
                    "valid": True,
                    "covered_tasks": 1,
                    "total_tasks": 1,
                    "invalid_reasons": [],
                },
                case_profile=case_profile,
            )

            self.assertEqual(outcome.decision, "accept")
            self.assertEqual(outcome.status, "candidate")

            registry = json.loads((Path(tmp) / "strategy_registry.json").read_text(encoding="utf-8"))
            self.assertEqual(registry[generated.strategy_id]["status"], "candidate")
            self.assertEqual(registry[generated.strategy_id]["origin_case_profile"]["regime"], "low-willingness")
            self.assertEqual(registry[generated.strategy_id]["last_case_profile"]["tasks"], 30)
            memory_lines = (Path(tmp) / "evolution_memory.jsonl").read_text(encoding="utf-8").splitlines()
            events = [json.loads(line)["event"] for line in memory_lines]
            self.assertIn("strategy_generated", events)
            self.assertIn("strategy_validated", events)
            self.assertIn("strategy_trial", events)

    def test_unsafe_generated_strategy_is_rejected_and_rolled_back(self):
        from autosolver_agent.evolution import EvolutionManager

        with tempfile.TemporaryDirectory() as tmp:
            manager = EvolutionManager(Path(tmp))
            bad_path = Path(tmp) / "generated_strategies" / "gen_bad.py"
            bad_path.parent.mkdir(parents=True, exist_ok=True)
            bad_path.write_text(
                "import os\n\ndef propose(candidates, all_tasks, deadline, helpers):\n    return []\n",
                encoding="utf-8",
            )

            result = manager.safety_check(bad_path, strategy_id="gen_bad")

            self.assertFalse(result.passed)
            self.assertIn("unsafe import", result.reason)
            registry = json.loads((Path(tmp) / "strategy_registry.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["gen_bad"]["status"], "rejected")
            self.assertEqual(registry["gen_bad"]["rollback_action"], "removed_from_active_pool")

    def test_unbounded_while_loop_is_rejected_before_sandbox_execution(self):
        from autosolver_agent.evolution import EvolutionManager

        with tempfile.TemporaryDirectory() as tmp:
            manager = EvolutionManager(Path(tmp))
            bad_path = Path(tmp) / "generated_strategies" / "gen_loop.py"
            bad_path.parent.mkdir(parents=True, exist_ok=True)
            bad_path.write_text(
                "def propose(candidates, all_tasks, deadline, helpers):\n    while True:\n        pass\n",
                encoding="utf-8",
            )

            result = manager.safety_check(bad_path, strategy_id="gen_loop")

            self.assertFalse(result.passed)
            self.assertIn("while", result.reason)

    def test_generated_strategy_source_is_regime_aware_and_deadline_guarded(self):
        from autosolver_agent.evolution import EvolutionManager

        with tempfile.TemporaryDirectory() as tmp:
            manager = EvolutionManager(Path(tmp))
            low = manager.generate_strategy("low-willingness", "low planner probe")
            scarce = manager.generate_strategy("scarce", "scarce planner probe")

            low_source = low.path.read_text(encoding="utf-8")
            scarce_source = scarce.path.read_text(encoding="utf-8")

            self.assertNotEqual(low_source, scarce_source)
            self.assertIn("low_willingness", low_source)
            self.assertIn("scarce", scarce_source)
            self.assertIn("time_left", low_source)
            self.assertIn("deadline", scarce_source)

    def test_trusted_strategy_retrieval_prefers_similar_case_profiles(self):
        from autosolver_agent.evolution import EvolutionManager

        with tempfile.TemporaryDirectory() as tmp:
            manager = EvolutionManager(Path(tmp))
            generated_dir = Path(tmp) / "generated_strategies"
            generated_dir.mkdir(exist_ok=True)
            similar_path = generated_dir / "gen_large_similar.py"
            far_path = generated_dir / "gen_large_far.py"
            similar_path.write_text("def propose(candidates, all_tasks, deadline, helpers):\n    return []\n", encoding="utf-8")
            far_path.write_text("def propose(candidates, all_tasks, deadline, helpers):\n    return []\n", encoding="utf-8")
            (Path(tmp) / "strategy_registry.json").write_text(
                json.dumps(
                    {
                        "gen_large_far": {
                            "status": "candidate",
                            "target_regime": "large",
                            "file": str(far_path),
                            "accepted": 5,
                            "rejected": 0,
                            "attempts": 5,
                            "last_case_profile": {
                                "regime": "large",
                                "tasks": 200,
                                "couriers": 400,
                                "rows": 9000,
                                "avg_willingness": 0.9,
                                "has_bundles": True,
                            },
                        },
                        "gen_large_similar": {
                            "status": "candidate",
                            "target_regime": "large",
                            "file": str(similar_path),
                            "accepted": 1,
                            "rejected": 0,
                            "attempts": 1,
                            "last_case_profile": {
                                "regime": "large",
                                "tasks": 40,
                                "couriers": 80,
                                "rows": 1200,
                                "avg_willingness": 0.55,
                                "has_bundles": True,
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            trusted = manager.trusted_strategies(
                "large",
                {
                    "regime": "large",
                    "tasks": 42,
                    "couriers": 82,
                    "rows": 1250,
                    "avg_willingness": 0.53,
                    "has_bundles": True,
                },
            )

            self.assertEqual(trusted[0]["strategy_id"], "gen_large_similar")
            self.assertGreater(trusted[0]["similarity"], trusted[1]["similarity"])

    def test_run_agent_emits_evolution_events_without_changing_solver_contract(self):
        from autosolver_agent import system

        seen_events: list[dict] = []

        def observer(event):
            seen_events.append(event)

        fake_module = mock.Mock()
        fake_module._solution_expected_cost.return_value = 1.0
        fake_module._fallback_official_greedy.return_value = [("T0000", ["C000"])]
        fake_module._solve_single_task_multidispatch.return_value = [("T0000", ["C000"])]
        fake_module._solve_disjoint_then_multidispatch.return_value = [("T0000", ["C000"])]
        fake_module._solve_pair_potential_matching.return_value = [("T0000", ["C000"])]
        fake_module._solve_sparse_cover.return_value = [("T0000", ["C000"])]
        fake_module._solve_low_global_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_low_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_scarce_k2_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_scarce_bundle_mcf_enum.return_value = [("T0000", ["C000"])]
        fake_module.solve.return_value = [("T0000", ["C000"])]

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(system, "EVOLUTION_ROOT", Path(tmp)), mock.patch.object(system, "load_solver", return_value=fake_module), mock.patch.object(system, "parse_candidates", return_value=([("T0000", ("T0000",), "C000", 1.0, 0.9, 0)], {"T0000"})), mock.patch.object(system, "infer_regime", return_value="large"), mock.patch.object(system, "summarize_solution", return_value={"valid": True, "covered_tasks": 1, "total_tasks": 1, "groups": 1, "used_couriers": 1, "uncovered_tasks": [], "riders_per_group": {}, "tasks_per_group": {}, "invalid_reasons": []}):
            report = system.run_agent("task_id_list\nT0000\tC000\t1\t0.9\n", budget_s=1.0, observer=observer)

        self.assertEqual(report["status"], "ok")
        seen = [event["type"] for event in seen_events]
        self.assertIn("evolution_generate", seen)
        self.assertIn("evolution_validate", seen)
        self.assertIn("evolution_trial", seen)
        self.assertIn("evolution", report)
        self.assertIn("case_profile", report["evolution"])
        self.assertIn("generated_strategy", report["evolution"])
        self.assertIn("trusted_details", report["evolution"])
        self.assertIn("mode", report["evolution"])
        trial_event = next(event for event in seen_events if event["type"] == "evolution_trial")
        self.assertIn("reason", trial_event)
        self.assertIn("reason_label", trial_event)
        self.assertIn("reason_detail", trial_event)
        self.assertIn("decision_action", trial_event)
        self.assertIn("rollback_label", trial_event)
        self.assertIn("elapsed_ms", trial_event)
        self.assertIn("trial_budget_ms", trial_event)

    def test_rejected_generated_strategy_rolls_back_without_mutating_solver_file(self):
        from autosolver_agent import system

        seen: list[str] = []

        def observer(event):
            seen.append(event["type"])

        fake_module = mock.Mock()
        fake_module._solution_expected_cost.return_value = 1.0
        fake_module._fallback_official_greedy.return_value = [("T0000", ["C000"])]
        fake_module._solve_single_task_multidispatch.return_value = [("T0000", ["C000"])]
        fake_module._solve_disjoint_then_multidispatch.return_value = [("T0000", ["C000"])]
        fake_module._solve_pair_potential_matching.return_value = [("T0000", ["C000"])]
        fake_module._solve_sparse_cover.return_value = [("T0000", ["C000"])]
        fake_module._solve_low_global_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_low_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_scarce_k2_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_scarce_bundle_mcf_enum.return_value = [("T0000", ["C000"])]
        fake_module.solve.return_value = [("T0000", ["C000"])]

        with tempfile.TemporaryDirectory() as tmp:
            solver_path = Path(tmp) / "solver.py"
            solver_source = "def solve(input_text):\n    return []\n"
            solver_path.write_text(solver_source, encoding="utf-8")
            with mock.patch.object(system, "SOLVER_PATH", solver_path), mock.patch.object(system, "EVOLUTION_ROOT", Path(tmp) / "evolution"), mock.patch.object(system, "load_solver", return_value=fake_module), mock.patch.object(system, "parse_candidates", return_value=([("T0000", ("T0000",), "C000", 1.0, 0.9, 0)], {"T0000"})), mock.patch.object(system, "infer_regime", return_value="large"), mock.patch.object(system, "summarize_solution", return_value={"valid": True, "covered_tasks": 1, "total_tasks": 1, "groups": 1, "used_couriers": 1, "uncovered_tasks": [], "riders_per_group": {}, "tasks_per_group": {}, "invalid_reasons": []}):
                report = system.run_agent("task_id_list\nT0000\tC000\t1\t0.9\n", budget_s=1.0, observer=observer)

            self.assertEqual(solver_path.read_text(encoding="utf-8"), solver_source)
            self.assertIn("evolution_trial", seen)
            self.assertIn("evolution_rollback", seen)
            self.assertEqual(report["evolution"]["mode"], "experimental-track-no-solver-mutation")

    def test_accepted_generated_strategy_emits_promote_event(self):
        from autosolver_agent.evolution import TrialOutcome
        from autosolver_agent import system

        seen: list[str] = []

        def observer(event):
            seen.append(event["type"])

        fake_module = mock.Mock()
        fake_module._solution_expected_cost.return_value = 1.0
        fake_module._fallback_official_greedy.return_value = [("T0000", ["C000"])]
        fake_module._solve_single_task_multidispatch.return_value = [("T0000", ["C000"])]
        fake_module._solve_disjoint_then_multidispatch.return_value = [("T0000", ["C000"])]
        fake_module._solve_pair_potential_matching.return_value = [("T0000", ["C000"])]
        fake_module._solve_sparse_cover.return_value = [("T0000", ["C000"])]
        fake_module._solve_low_global_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_low_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_scarce_k2_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_scarce_bundle_mcf_enum.return_value = [("T0000", ["C000"])]
        fake_module.solve.return_value = [("T0000", ["C000"])]

        accepted_outcome = TrialOutcome(
            "gen_large_v001",
            "candidate",
            "accept",
            "improved experimental candidate",
            True,
            1.0,
            [("T0000", ["C000"])],
            0.5,
        )

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(system, "EVOLUTION_ROOT", Path(tmp)), mock.patch.object(system.EvolutionManager, "run_generated_strategy", return_value=accepted_outcome), mock.patch.object(system, "load_solver", return_value=fake_module), mock.patch.object(system, "parse_candidates", return_value=([("T0000", ("T0000",), "C000", 1.0, 0.9, 0)], {"T0000"})), mock.patch.object(system, "infer_regime", return_value="large"), mock.patch.object(system, "summarize_solution", return_value={"valid": True, "covered_tasks": 1, "total_tasks": 1, "groups": 1, "used_couriers": 1, "uncovered_tasks": [], "riders_per_group": {}, "tasks_per_group": {}, "invalid_reasons": []}):
            report = system.run_agent("task_id_list\nT0000\tC000\t1\t0.9\n", budget_s=1.0, observer=observer)

        self.assertEqual(report["status"], "ok")
        self.assertIn("evolution_trial", seen)
        self.assertIn("evolution_promote", seen)

    def test_trusted_strategy_memory_is_replayed_in_next_agent_run(self):
        from autosolver_agent import system

        seen: list[str] = []

        def observer(event):
            seen.append(event["type"])

        fake_module = mock.Mock()
        fake_module._solution_expected_cost.return_value = 1.0
        fake_module._fallback_official_greedy.return_value = [("T0000", ["C000"])]
        fake_module._solve_single_task_multidispatch.return_value = [("T0000", ["C000"])]
        fake_module._solve_disjoint_then_multidispatch.return_value = [("T0000", ["C000"])]
        fake_module._solve_pair_potential_matching.return_value = [("T0000", ["C000"])]
        fake_module._solve_sparse_cover.return_value = [("T0000", ["C000"])]
        fake_module._solve_low_global_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_low_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_scarce_k2_column_search.return_value = [("T0000", ["C000"])]
        fake_module._solve_scarce_bundle_mcf_enum.return_value = [("T0000", ["C000"])]
        fake_module.solve.return_value = [("T0000", ["C000"])]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generated_dir = root / "generated_strategies"
            generated_dir.mkdir()
            trusted_path = generated_dir / "gen_large_v000.py"
            trusted_path.write_text(
                "def propose(candidates, all_tasks, deadline, helpers):\n    return [('T0000', ['C000'])]\n",
                encoding="utf-8",
            )
            (root / "strategy_registry.json").write_text(
                json.dumps(
                    {
                        "gen_large_v000": {
                            "status": "candidate",
                            "target_regime": "large",
                            "file": str(trusted_path),
                            "accepted": 1,
                            "rejected": 0,
                            "attempts": 1,
                            "last_case_profile": {
                                "regime": "large",
                                "tasks": 40,
                                "couriers": 80,
                                "rows": 1200,
                                "avg_willingness": 0.5,
                                "has_bundles": True,
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(system, "EVOLUTION_ROOT", root), mock.patch.object(system, "load_solver", return_value=fake_module), mock.patch.object(system, "parse_candidates", return_value=([("T0000", ("T0000",), "C000", 1.0, 0.9, 0)], {"T0000"})), mock.patch.object(system, "infer_regime", return_value="large"), mock.patch.object(system, "summarize_solution", return_value={"valid": True, "covered_tasks": 1, "total_tasks": 1, "groups": 1, "used_couriers": 1, "uncovered_tasks": [], "riders_per_group": {}, "tasks_per_group": {}, "invalid_reasons": []}):
                report = system.run_agent("task_id_list\nT0000\tC000\t1\t0.9\n", budget_s=1.0, observer=observer)

        self.assertIn("gen_large_v000", report["evolution"]["trusted_recalled"])
        self.assertIn("evolution_recall", seen)
        self.assertIn("evolution_replay", seen)
        self.assertIn("similarity", report["evolution"]["trusted_details"][0])


if __name__ == "__main__":
    unittest.main()
