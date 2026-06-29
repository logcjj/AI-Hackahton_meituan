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
        self.assertEqual(
            [route["label"] for route in payload["routes"]],
            ["实时推理", "决策过程", "长期记忆", "订单池", "骑手运力"],
        )
        self.assertEqual(len(payload["entities"]["orders"]), len(contract.orders))
        self.assertEqual(len(payload["entities"]["riders"]), len(contract.couriers))
        self.assertEqual(len(payload["entities"]["merchants"]), len(contract.merchants))
        self.assertEqual(len(payload["decisions"]), len(contract.frames))
        self.assertEqual(len(payload["memory"]["items"]), len(contract.evolution_events))
        self.assertEqual(payload["memory"]["system"]["operating_model"], "global policy + profile memories + active recall + writeback feedback")
        self.assertEqual(
            [layer["id"] for layer in payload["memory"]["layers"]],
            ["global-policy", "rider-profile", "area-demand-profile", "order-risk-profile"],
        )
        self.assertEqual(
            [profile["profile_type"] for profile in payload["memory"]["profiles"]],
            ["rider", "area", "order"],
        )
        self.assertEqual(
            [step["id"] for step in payload["memory"]["recall_chain"]],
            ["hit", "inject", "decide", "writeback"],
        )
        self.assertEqual(
            [step["id"] for step in payload["memory"]["writeback_loop"]],
            ["new-memory", "curated-memory", "active-memory", "feedback-memory"],
        )
        self.assertEqual(payload["map"]["tile_provider"], "cartodb-light-nolabels-leaflet")
        self.assertEqual(payload["map"]["privacy"]["entity_labels"], "anonymized")
        self.assertEqual(payload["map"]["privacy"]["road_labels"], "hidden_by_default")
        self.assertEqual(payload["map"]["aliases"]["merchants"][payload["map"]["anchors"]["merchants"][0]["id"]], "M-01")
        self.assertEqual(payload["map"]["aliases"]["riders"][payload["map"]["anchors"]["riders"][0]["id"]], "R-01")
        self.assertEqual(payload["map"]["aliases"]["orders"][payload["map"]["anchors"]["orders"][0]["id"]], "O-001")
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
        merchant_anchor = payload["map"]["anchors"]["merchants"][0]
        rider_anchor = payload["map"]["anchors"]["riders"][0]
        order_anchor = payload["map"]["anchors"]["orders"][0]

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
            "memory_scope",
            "formation_channel",
            "context_summary",
            "strategy_summary",
            "decision_result",
            "dispatch_effect",
            "effect_feedback",
            "confidence",
            "recall_count",
            "latest_hit_time_label",
        ):
            self.assertIn(key, memory)
        self.assertRegex(merchant_anchor["map_label"], r"^M-\d{2}$")
        self.assertRegex(rider_anchor["map_label"], r"^R-\d{2}$")
        self.assertRegex(order_anchor["map_label"], r"^O-\d{3}$")
        self.assertNotEqual(merchant_anchor["map_label"], merchant_anchor["label"])
        self.assertNotEqual(rider_anchor["map_label"], rider_anchor["label"])

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
        start = html.index('<script id="dispatch-workbench-bootstrap" type="application/json">')
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
