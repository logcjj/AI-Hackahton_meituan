from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from web_agent_demo.compare_engine import run_comparison
from web_agent_demo.memory_engine import SimulationMemoryStore, rank_algorithms_with_predictor
from web_agent_demo.simulation_engine import SimulationControls, advance_simulation, create_simulation_session


class SimulationMemoryEngineTest(unittest.TestCase):
    def test_compare_run_writes_secret_free_events_and_strategy_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SimulationMemoryStore(Path(tmp))
            start = create_simulation_session(
                "commerce_peak",
                seed="memory-write",
                controls=SimulationControls(courier_count=6, order_intensity=0.8, burstiness=0.8),
            )
            advanced = advance_simulation(start.session, start.tick, advance_seconds=60)

            comparison = run_comparison(start.session, advanced.tick, memory_store=store, memory_mode="read-write")

            events = [json.loads(line) for line in (Path(tmp) / "memory_events.jsonl").read_text(encoding="utf-8").splitlines()]
            event_types = {event["event_type"] for event in events}
            registry = json.loads((Path(tmp) / "strategy_registry.json").read_text(encoding="utf-8"))

            self.assertIn("scenario_seen", event_types)
            self.assertIn("compare_completed", event_types)
            self.assertIn("strategy_selected", event_types)
            self.assertIn("autosolver_agent", registry)
            self.assertGreaterEqual(registry["autosolver_agent"]["attempts"], 1)
            learned_sources = [
                algorithm_id
                for algorithm_id, item in registry.items()
                if algorithm_id != "autosolver_agent" and int(item.get("selected_count", 0)) > 0
            ]
            self.assertEqual(learned_sources, [comparison.selected.source_algorithm_id])
            self.assertTrue(all(event["privacy"]["secret_free"] for event in events))
            self.assertEqual(comparison.memory.mode, "read-write")

    def test_similar_strategy_memory_changes_autosolver_agent_ranking(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SimulationMemoryStore(Path(tmp))
            start = create_simulation_session(
                "rain_low_willingness",
                seed="memory-rank",
                controls=SimulationControls(courier_count=6, order_intensity=0.85, burstiness=0.8, weather="rain", congestion_level=0.8),
            )
            advanced = advance_simulation(start.session, start.tick, advance_seconds=60)
            baseline = run_comparison(start.session, advanced.tick)
            features = baseline.compare_run.scenario_features
            store.register_evolution_candidate("memory_cost_bias", "cost_greedy", features, "Prefer cost greedy in similar rain scenes.")
            first_trial = store.record_evolution_trial("memory_cost_bias", True, {"score": 98.0}, features, "Cost greedy won historical rain replay.")
            second_trial = store.record_evolution_trial("memory_cost_bias", True, {"score": 99.0}, features, "Cost greedy promoted after repeated rain replay.")

            comparison = run_comparison(
                start.session,
                advanced.tick,
                memory_store=store,
                memory_mode="read-only",
                predictor_mode="fallback",
            )
            results_by_id = {result.algorithm_id: result for result in comparison.results}

            self.assertEqual(first_trial["status"], "candidate")
            self.assertEqual(second_trial["status"], "promoted")
            self.assertEqual(comparison.selected.algorithm_id, "autosolver_agent")
            self.assertEqual(comparison.predictor.ranked_algorithms[0]["algorithm_id"], "cost_greedy")
            self.assertIn("cost_greedy", comparison.memory.effect_on_ranking)
            self.assertIn("Cost Greedy", comparison.selected.reason)
            self.assertEqual(
                {(item.order_id, item.courier_id) for item in comparison.selected.assignments},
                {(item.order_id, item.courier_id) for item in results_by_id["cost_greedy"].assignments},
            )

    def test_predictor_auto_mode_uses_fallback_without_env(self):
        start = create_simulation_session("commerce_peak", seed="memory-predictor", controls=SimulationControls(courier_count=4))
        advanced = advance_simulation(start.session, start.tick, advance_seconds=20)
        comparison = run_comparison(start.session, advanced.tick, algorithms=("nearest_greedy", "cost_greedy"))

        trace = rank_algorithms_with_predictor(
            comparison.compare_run.scenario_features,
            comparison.results,
            comparison.memory,
            mode="auto",
            env={},
        )

        self.assertFalse(trace.used_external_api)
        self.assertEqual(trace.secret_handling, "env-only-redacted")
        self.assertEqual(trace.status, "skipped")
        self.assertTrue(trace.ranked_algorithms)

    def test_evolution_trial_promotes_and_rolls_back_with_audit_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SimulationMemoryStore(Path(tmp))
            start = create_simulation_session("scarce_repair", seed="memory-evolve", controls=SimulationControls(courier_count=3))
            advanced = advance_simulation(start.session, start.tick, advance_seconds=60)
            features = run_comparison(start.session, advanced.tick).compare_run.scenario_features

            store.register_evolution_candidate("generated_sparse_probe", "sparse_cover", features, "Generate sparse repair probe.")
            candidate = store.record_evolution_trial("generated_sparse_probe", True, {"score": 72.0}, features, "Accepted first sparse repair trial.")
            promoted = store.record_evolution_trial("generated_sparse_probe", True, {"score": 75.0}, features, "Promoted after repeated sparse repair win.")
            rolled_back = store.record_evolution_trial("generated_bad_probe", False, {"score": 18.0}, features, "Rolled back quality regression.")

            events = [json.loads(line) for line in (Path(tmp) / "memory_events.jsonl").read_text(encoding="utf-8").splitlines()]
            event_types = {event["event_type"] for event in events}

            self.assertEqual(candidate["status"], "candidate")
            self.assertEqual(promoted["status"], "promoted")
            self.assertEqual(rolled_back["status"], "rolled_back")
            self.assertIn("evolution_candidate_generated", event_types)
            self.assertIn("evolution_promoted", event_types)
            self.assertIn("evolution_rolled_back", event_types)


if __name__ == "__main__":
    unittest.main()
