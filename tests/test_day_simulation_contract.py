from __future__ import annotations

import unittest

from web_agent_demo.day_simulation import (
    DAY_SIMULATION_CONTRACT_VERSION,
    DAY_SIMULATION_ENDPOINTS,
    build_contract_preview,
    day_contract_to_dict,
    day_scenario_catalog,
)


class DaySimulationContractTest(unittest.TestCase):
    def test_catalog_declares_full_day_replay_requirements(self):
        scenarios = day_scenario_catalog()
        scenario = scenarios[0]

        self.assertEqual(scenario.id, "weekday_full_day")
        self.assertLess(scenario.day_start_s, scenario.day_end_s)
        self.assertIn("breakfast", scenario.demand_phases)
        self.assertIn("lunch_peak", scenario.demand_phases)
        self.assertIn("dinner_peak", scenario.demand_phases)
        self.assertIn("courier_shortage", scenario.shock_profiles)
        self.assertIn("nearest_greedy", scenario.algorithms)
        self.assertIn("autosolver_agent", scenario.algorithms)
        self.assertEqual(scenario.default_controls.baseline_algorithm_id, "nearest_greedy")
        self.assertEqual(scenario.default_controls.challenger_algorithm_id, "autosolver_agent")

    def test_contract_preview_has_required_top_level_sections(self):
        payload = day_contract_to_dict(build_contract_preview())

        self.assertEqual(payload["contract_version"], DAY_SIMULATION_CONTRACT_VERSION)
        for key in (
            "scenario",
            "merchants",
            "couriers",
            "orders",
            "shocks",
            "time_slices",
            "baseline_run",
            "challenger_run",
            "frames",
            "reasoning_traces",
            "evolution_events",
            "api_endpoints",
            "privacy",
        ):
            self.assertIn(key, payload)
        self.assertEqual(payload["api_endpoints"], DAY_SIMULATION_ENDPOINTS)
        self.assertEqual(payload["privacy"]["secret_handling"], "env-only-redacted")

    def test_side_by_side_frame_connects_metrics_reasoning_and_memory(self):
        payload = day_contract_to_dict(build_contract_preview())
        frame = payload["frames"][0]
        reasoning = payload["reasoning_traces"][0]
        memory_event = payload["evolution_events"][0]

        self.assertEqual(frame["baseline"]["algorithm_id"], "nearest_greedy")
        self.assertEqual(frame["challenger"]["algorithm_id"], "autosolver_agent")
        self.assertGreater(frame["delta"]["time_saved_s"], 0)
        self.assertGreater(frame["delta"]["cost_saved_yuan"], 0)
        self.assertIn(reasoning["id"], frame["reasoning_trace_ids"])
        self.assertIn(memory_event["id"], frame["memory_event_ids"])
        self.assertEqual(reasoning["expected_impact"]["headline"], frame["delta"]["headline"])
        self.assertEqual(memory_event["chosen_algorithm_id"], "autosolver_agent")
        self.assertTrue(memory_event["writeback"])
        self.assertEqual(memory_event["secret_handling"], "env-only-redacted")
        self.assertEqual(frame["baseline"]["simulation_trace"]["engine_id"], "courier-agent-sim-v1")
        self.assertEqual(frame["challenger"]["simulation_trace"]["engine_provider"], "AutoSolver CourierSim in-process event simulator")
        self.assertEqual(frame["challenger"]["simulation_trace"]["engine_mode"], "discrete-event-agent-simulation")
        self.assertFalse(frame["challenger"]["simulation_trace"]["map_labels_visible"])

    def test_orders_time_slices_and_runs_share_stable_ids(self):
        payload = day_contract_to_dict(build_contract_preview())
        order_ids = {order["id"] for order in payload["orders"]}
        slice_order_ids = set(payload["time_slices"][0]["order_ids"])
        frame = payload["frames"][0]

        self.assertTrue(slice_order_ids.issubset(order_ids))
        self.assertEqual(payload["baseline_run"]["algorithm_id"], frame["baseline"]["algorithm_id"])
        self.assertEqual(payload["challenger_run"]["algorithm_id"], frame["challenger"]["algorithm_id"])
        self.assertIn(frame["id"], payload["baseline_run"]["frame_ids"])
        self.assertIn(frame["id"], payload["challenger_run"]["frame_ids"])
        self.assertEqual(frame["baseline"]["assignments"][0]["order_id"], payload["orders"][0]["id"])
        self.assertEqual(frame["challenger"]["assignments"][0]["order_id"], payload["orders"][0]["id"])
        self.assertTrue(frame["challenger"]["simulation_trace"]["courier_tracks"])
        self.assertTrue(frame["challenger"]["simulation_trace"]["event_queue"])
        self.assertGreaterEqual(frame["challenger"]["simulation_trace"]["emitted_tick_count"], 3)


if __name__ == "__main__":
    unittest.main()
