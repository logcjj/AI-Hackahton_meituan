from __future__ import annotations

import unittest

from web_agent_demo.compare_engine import DEFAULT_ALGORITHMS, run_comparison
from web_agent_demo.simulation_engine import SimulationControls, advance_simulation, create_simulation_session, simulation_to_dict


class CompareEngineTest(unittest.TestCase):
    def test_default_portfolio_returns_uniform_algorithm_results(self):
        start = create_simulation_session(
            "commerce_peak",
            seed="compare-default",
            controls=SimulationControls(courier_count=6, order_intensity=0.85, burstiness=0.85, congestion_level=0.55),
        )
        advanced = advance_simulation(start.session, start.tick, advance_seconds=60)

        comparison = run_comparison(start.session, advanced.tick)
        results_by_id = {result.algorithm_id: result for result in comparison.results}

        self.assertEqual(tuple(results_by_id), DEFAULT_ALGORITHMS)
        self.assertEqual(comparison.compare_run.status, "completed")
        self.assertEqual(comparison.compare_run.baseline_algorithm_id, "nearest_greedy")
        self.assertEqual(comparison.selected.algorithm_id, "autosolver_agent")
        self.assertGreater(len(comparison.decision_points), 0)
        self.assertNotIn("S1", results_by_id)
        for result in comparison.results:
            self.assertEqual(result.metrics.total_orders, len(advanced.tick.active_order_ids))
            self.assertGreaterEqual(result.metrics.coverage_rate, 0.0)
            self.assertLessEqual(result.metrics.coverage_rate, 1.0)
            self.assertLessEqual(result.metrics.runtime_ms, comparison.compare_run.time_budget_ms)
            self.assertIn(result.status, {"selected", "evaluated"})
            self.assertEqual(len({assignment.order_id for assignment in result.assignments}), len(result.assignments))
            self.assertEqual(len({assignment.courier_id for assignment in result.assignments}), len(result.assignments))

        baseline = results_by_id["nearest_greedy"]
        self.assertEqual(baseline.metrics.relative_to_baseline["cost_delta_pct"], 0.0)
        self.assertEqual(baseline.metrics.relative_to_baseline["eta_delta_pct"], 0.0)

    def test_empty_tick_returns_completed_noop_compare(self):
        start = create_simulation_session("commerce_peak", seed="compare-empty", controls=SimulationControls(courier_count=4))

        comparison = run_comparison(start.session, start.tick, algorithms=("nearest_greedy", "autosolver_agent"))

        self.assertEqual(comparison.compare_run.status, "completed")
        self.assertEqual(comparison.selected.algorithm_id, "autosolver_agent")
        for result in comparison.results:
            self.assertEqual(result.metrics.total_orders, 0)
            self.assertEqual(result.metrics.coverage_rate, 1.0)
            self.assertEqual(result.assignments, ())
            self.assertEqual(result.metrics.no_accept_risk, 0.0)
            self.assertEqual(result.metrics.timeout_risk, 0.0)

    def test_scarce_courier_burst_exposes_uncovered_order_risk(self):
        start = create_simulation_session(
            "scarce_repair",
            seed="compare-scarce",
            controls=SimulationControls(courier_count=2, order_intensity=0.95, burstiness=1.0),
        )
        advanced = advance_simulation(start.session, start.tick, advance_seconds=60)

        comparison = run_comparison(start.session, advanced.tick)

        self.assertGreater(len(advanced.tick.active_order_ids), len(advanced.tick.couriers))
        for result in comparison.results:
            self.assertLessEqual(result.metrics.covered_orders, len(advanced.tick.couriers))
            self.assertLess(result.metrics.coverage_rate, 1.0)
            self.assertIn("uncovered_orders", result.risk_flags)

    def test_risk_aware_greedy_reduces_low_willingness_acceptance_risk(self):
        start = create_simulation_session(
            "rain_low_willingness",
            seed="compare-rain",
            controls=SimulationControls(courier_count=6, order_intensity=0.8, burstiness=0.75, weather="rain", congestion_level=0.82),
        )
        advanced = advance_simulation(start.session, start.tick, advance_seconds=60)

        comparison = run_comparison(start.session, advanced.tick)
        results_by_id = {result.algorithm_id: result for result in comparison.results}

        self.assertLessEqual(
            results_by_id["risk_aware_greedy"].metrics.no_accept_risk,
            results_by_id["nearest_greedy"].metrics.no_accept_risk,
        )
        self.assertGreater(results_by_id["flow_mcf"].metrics.score, 0.0)

    def test_compare_result_is_serializable_for_api_payloads(self):
        start = create_simulation_session("commerce_peak", seed="compare-serializable", controls=SimulationControls(courier_count=4))
        advanced = advance_simulation(start.session, start.tick, advance_seconds=20)

        payload = simulation_to_dict(run_comparison(start.session, advanced.tick))

        self.assertIn("compare_run", payload)
        self.assertIn("results", payload)
        self.assertIn("decision_points", payload)
        self.assertEqual(payload["compare_run"]["selected_algorithm_id"], "autosolver_agent")
        self.assertTrue(payload["timeline_delta"])

    def test_unknown_algorithm_is_reported_as_failed_not_evaluated(self):
        start = create_simulation_session("commerce_peak", seed="compare-unknown", controls=SimulationControls(courier_count=4))
        advanced = advance_simulation(start.session, start.tick, advance_seconds=20)

        comparison = run_comparison(start.session, advanced.tick, algorithms=("unknown_algo", "nearest_greedy"))
        results_by_id = {result.algorithm_id: result for result in comparison.results}

        self.assertEqual(results_by_id["unknown_algo"].status, "failed")
        self.assertEqual(comparison.selected.algorithm_id, "nearest_greedy")


if __name__ == "__main__":
    unittest.main()
