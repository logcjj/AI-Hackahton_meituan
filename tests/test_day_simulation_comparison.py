from __future__ import annotations

import unittest

from web_agent_demo.day_simulation import (
    DaySimulationControls,
    day_comparison_to_dict,
    run_full_day_comparison,
)


class DaySimulationComparisonTest(unittest.TestCase):
    def _payload(self, seed: str = "comparison-day") -> dict:
        controls = DaySimulationControls(courier_count=24, order_scale=0.55, weather="mixed", congestion_profile="weekday")
        return day_comparison_to_dict(run_full_day_comparison(seed=seed, controls=controls))

    def test_same_seed_comparison_is_deterministic_and_same_stream(self):
        left = self._payload("same-stream")
        right = self._payload("same-stream")
        changed = self._payload("changed-stream")

        self.assertEqual(left, right)
        self.assertNotEqual(left["orders"], changed["orders"])
        self.assertEqual(left["baseline_run"]["metrics"]["total_orders"], len(left["orders"]))
        self.assertEqual(left["challenger_run"]["metrics"]["total_orders"], len(left["orders"]))
        self.assertEqual(left["baseline_run"]["metrics"]["assigned_orders"], len(left["orders"]))
        self.assertEqual(left["challenger_run"]["metrics"]["assigned_orders"], len(left["orders"]))

    def test_autosolver_improves_cumulative_time_cost_and_risk(self):
        payload = self._payload("metric-day")
        baseline = payload["baseline_run"]["metrics"]
        challenger = payload["challenger_run"]["metrics"]

        self.assertEqual(payload["baseline_run"]["algorithm_id"], "nearest_greedy")
        self.assertEqual(payload["challenger_run"]["algorithm_id"], "autosolver_agent")
        self.assertLess(challenger["total_time_cost_s"], baseline["total_time_cost_s"])
        self.assertLess(challenger["total_cost_yuan"], baseline["total_cost_yuan"])
        self.assertLess(challenger["avg_eta_s"], baseline["avg_eta_s"])
        self.assertLess(challenger["timeout_risk"], baseline["timeout_risk"])
        self.assertEqual(challenger["coverage_rate"], 1.0)
        self.assertGreater(baseline["gross_revenue_yuan"], 0)

    def test_frames_compare_identical_slice_orders_and_valid_deltas(self):
        payload = self._payload("frame-day")

        self.assertGreater(len(payload["frames"]), 10)
        self.assertEqual(len(payload["frames"]), len(payload["reasoning_traces"]))
        trace_by_id = {trace["id"]: trace for trace in payload["reasoning_traces"]}
        slice_by_id = {time_slice["id"]: time_slice for time_slice in payload["time_slices"]}
        for frame in payload["frames"]:
            time_slice = slice_by_id[frame["time_slice_id"]]
            self.assertEqual(frame["baseline"]["active_order_ids"], time_slice["order_ids"])
            self.assertEqual(frame["challenger"]["active_order_ids"], time_slice["order_ids"])
            self.assertEqual(
                [item["order_id"] for item in frame["baseline"]["assignments"]],
                [item["order_id"] for item in frame["challenger"]["assignments"]],
            )
            expected_time = round(
                frame["baseline"]["metrics"]["total_time_cost_s"] - frame["challenger"]["metrics"]["total_time_cost_s"],
                3,
            )
            expected_cost = round(frame["baseline"]["metrics"]["total_cost_yuan"] - frame["challenger"]["metrics"]["total_cost_yuan"], 3)
            self.assertEqual(frame["delta"]["time_saved_s"], expected_time)
            self.assertEqual(frame["delta"]["cost_saved_yuan"], expected_cost)
            self.assertIn(frame["reasoning_trace_ids"][0], trace_by_id)
            self.assertEqual(frame["baseline"]["simulation_trace"]["engine_id"], "courier-agent-sim-v1")
            self.assertEqual(frame["challenger"]["simulation_trace"]["engine_mode"], "discrete-event-agent-simulation")
            self.assertGreaterEqual(frame["challenger"]["simulation_trace"]["track_count"], 1)
            self.assertGreaterEqual(frame["challenger"]["simulation_trace"]["event_count"], 3)
            self.assertFalse(frame["challenger"]["simulation_trace"]["map_labels_visible"])

    def test_reasoning_traces_surface_key_decision_points(self):
        payload = self._payload("reasoning-day")
        slice_by_id = {time_slice["id"]: time_slice for time_slice in payload["time_slices"]}
        shock_frames = [frame for frame in payload["frames"] if slice_by_id[frame["time_slice_id"]]["shock_ids"]]

        self.assertTrue(any(frame["highlighted_order_ids"] for frame in payload["frames"]))
        self.assertTrue(any(frame["highlighted_courier_ids"] for frame in payload["frames"]))
        self.assertTrue(payload["reasoning_traces"])
        for trace in payload["reasoning_traces"][:8]:
            algorithm_ids = {score["algorithm_id"] for score in trace["candidate_scores"]}
            self.assertEqual(algorithm_ids, {"nearest_greedy", "autosolver_agent"})
            self.assertEqual(trace["time_budget_ms"], 10_000)
            self.assertIn(trace["evidence"]["demand_phase"], {"lunch_peak", "dinner_peak", "night_supply_gap"})
            self.assertIn("AutoSolver", trace["rationale"])
            self.assertEqual(len(trace["memory_event_ids"]), 3)
        self.assertGreater(len(shock_frames), 0)


if __name__ == "__main__":
    unittest.main()
