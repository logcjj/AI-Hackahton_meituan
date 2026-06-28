from __future__ import annotations

import json
import unittest

from web_agent_demo.day_simulation import DaySimulationControls, run_full_day_comparison
from web_agent_demo.dispatch_workbench_data import WORKBENCH_MODEL_VERSION, build_dispatch_workbench_payload


class DispatchWorkbenchDataTest(unittest.TestCase):
    def test_workbench_payload_has_full_day_dispatch_sections(self):
        contract = run_full_day_comparison(
            seed="workbench-contract",
            controls=DaySimulationControls(courier_count=18, order_scale=0.38, weather="mixed", congestion_profile="weekday"),
        )

        payload = build_dispatch_workbench_payload(contract)

        self.assertEqual(payload["model_version"], WORKBENCH_MODEL_VERSION)
        self.assertEqual(payload["source"]["scenario_id"], "weekday_full_day")
        self.assertEqual(
            [route["id"] for route in payload["routes"]],
            ["live", "decisions", "memory", "orders", "riders"],
        )
        self.assertEqual(len(payload["entities"]["orders"]), len(contract.orders))
        self.assertEqual(len(payload["entities"]["riders"]), len(contract.couriers))
        self.assertEqual(len(payload["entities"]["merchants"]), len(contract.merchants))
        self.assertEqual(len(payload["decisions"]), len(contract.frames))
        self.assertEqual(len(payload["memory"]["items"]), len(contract.evolution_events))
        self.assertGreater(payload["inspection"]["order_count"], 100)
        self.assertEqual(payload["inspection"]["rider_count"], 18)
        self.assertTrue(payload["inspection"]["full_day_preloaded"])
        self.assertTrue(payload["inspection"]["deterministic"])

    def test_orders_riders_decisions_memory_have_required_fields(self):
        contract = run_full_day_comparison(
            seed="workbench-fields",
            controls=DaySimulationControls(courier_count=18, order_scale=0.38, weather="mixed", congestion_profile="weekday"),
        )

        payload = build_dispatch_workbench_payload(contract)
        order = payload["entities"]["orders"][0]
        rider = payload["entities"]["riders"][0]
        decision = payload["decisions"][0]
        memory = payload["memory"]["items"][0]

        for key in (
            "id",
            "merchant_label",
            "created_at_label",
            "promised_at_label",
            "status",
            "risk_level",
            "business_area",
            "entered_inference",
            "baseline_result",
            "our_result",
        ):
            self.assertIn(key, order)
        for key in (
            "id",
            "name",
            "online_state",
            "shift_label",
            "business_area",
            "current_load",
            "task_chain",
            "estimated_free_at_label",
            "performance",
            "mini_map",
        ):
            self.assertIn(key, rider)
        for key in (
            "trigger_time_label",
            "trigger_reason",
            "input_orders",
            "candidate_riders",
            "filtering_process",
            "scoring_process",
            "final_actions",
            "abandoned_actions",
            "round_result",
            "result_writeback",
        ):
            self.assertIn(key, decision)
        for key in (
            "trigger_scenario",
            "context_summary",
            "strategy_summary",
            "decision_result",
            "effect_feedback",
            "confidence",
            "recall_count",
            "latest_hit_time_label",
        ):
            self.assertIn(key, memory)

    def test_workbench_payload_is_deterministic_and_json_serializable(self):
        controls = DaySimulationControls(courier_count=18, order_scale=0.38, weather="mixed", congestion_profile="weekday")
        first = build_dispatch_workbench_payload(run_full_day_comparison(seed="stable-workbench", controls=controls))
        second = build_dispatch_workbench_payload(run_full_day_comparison(seed="stable-workbench", controls=controls))

        self.assertEqual(first, second)
        encoded = json.dumps(first, ensure_ascii=False, sort_keys=True)
        self.assertIn('"model_version": "dispatch-workbench-v1"', encoded)
        self.assertIn('"full_day_preloaded": true', encoded)

    def test_home_page_bootstrap_exposes_inspectable_workbench_model(self):
        from web_agent_demo.server import render_index

        html = render_index()
        start = html.index('<script id="day-replay-bootstrap" type="application/json">')
        start = html.index(">", start) + 1
        end = html.index("</script>", start)
        payload = json.loads(html[start:end])
        workbench = payload["workbench"]

        self.assertEqual(workbench["model_version"], WORKBENCH_MODEL_VERSION)
        self.assertEqual(workbench["inspection"]["order_count"], len(payload["contract"]["orders"]))
        self.assertEqual(workbench["inspection"]["rider_count"], len(payload["contract"]["couriers"]))
        self.assertEqual(workbench["routes"][0]["path"], "#/live")
        self.assertGreater(len(workbench["timeline"]["events"]), len(workbench["entities"]["orders"]))


if __name__ == "__main__":
    unittest.main()
