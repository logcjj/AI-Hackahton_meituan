from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from web_agent_demo import server


class SimulationApiContractTest(unittest.TestCase):
    def setUp(self):
        server._SIMULATION_RUNTIME.clear()
        server._COMPARE_RUNTIME.clear()

    def test_simulation_compare_api_payload_chain(self):
        session_payload = server._create_simulation_session_payload(
            {
                "scenario_id": "commerce_peak",
                "seed": "api-chain",
                "controls": {"courier_count": 5, "order_intensity": 0.85, "burstiness": 0.85},
            }
        )
        tick_payload = server._advance_simulation_payload(
            {
                "session_id": session_payload["session"]["session_id"],
                "advance_seconds": 60,
                "compare_if_due": True,
            }
        )
        compare_payload = server._run_compare_payload(
            {
                "session_id": session_payload["session"]["session_id"],
                "tick_id": tick_payload["tick"]["tick_id"],
                "time_budget_ms": 10_000,
                "memory_mode": "off",
            }
        )
        fetched = server._get_compare_payload(compare_payload["compare_run"]["compare_run_id"])

        self.assertEqual(session_payload["status"], "ok")
        self.assertEqual(tick_payload["status"], "ok")
        self.assertEqual(compare_payload["status"], "ok")
        self.assertEqual(fetched["compare_run"]["compare_run_id"], compare_payload["compare_run"]["compare_run_id"])
        self.assertIn("autosolver_agent", {result["algorithm_id"] for result in compare_payload["results"]})
        self.assertEqual(compare_payload["memory"]["mode"], "off")
        self.assertEqual(compare_payload["predictor"]["secret_handling"], "env-only-redacted")
        self.assertTrue(compare_payload["decision_points"])

    def test_memory_and_predictor_api_payloads_do_not_require_external_env(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(server, "SIMULATION_MEMORY_ROOT", Path(tmp)):
            recall = server._memory_recall_payload({"scenario_id": ["commerce_peak"], "weather": ["clear"]})
            dry_event = server._memory_event_payload(
                {
                    "dry_run": True,
                    "event": {
                        "event_type": "scenario_seen",
                        "features": {"scenario_id": "commerce_peak", "weather": "clear"},
                    },
                }
            )
            predictor = server._predictor_rank_payload({"candidate_algorithms": ["nearest_greedy", "cost_greedy"], "mode": "auto"})

        self.assertEqual(recall["status"], "ok")
        self.assertEqual(recall["recall"]["mode"], "read-only")
        self.assertTrue(dry_event["accepted"])
        self.assertEqual(predictor["predictor"]["used_external_api"], False)
        self.assertEqual(predictor["predictor"]["secret_handling"], "env-only-redacted")
        self.assertEqual([item["algorithm_id"] for item in predictor["ranked_algorithms"]], ["nearest_greedy", "cost_greedy"])


if __name__ == "__main__":
    unittest.main()
