from __future__ import annotations

import json
import unittest

from web_agent_demo.day_simulation import (
    DaySimulationControls,
    day_comparison_to_dict,
    run_full_day_comparison,
)


class DaySimulationMemoryEvolutionTest(unittest.TestCase):
    def _payload(self, env: dict[str, str] | None = None, memory_mode: str = "read-write") -> dict:
        controls = DaySimulationControls(courier_count=16, order_scale=0.35, memory_mode=memory_mode, predictor_mode="auto")
        return day_comparison_to_dict(run_full_day_comparison(seed="memory-day", controls=controls, env=env or {}))

    def test_memory_events_cover_recall_writeback_and_policy_shift(self):
        payload = self._payload()
        event_types = {event["event_type"] for event in payload["evolution_events"]}

        self.assertEqual(event_types, {"memory_recall", "memory_writeback", "future_policy_shift"})
        self.assertEqual(len(payload["evolution_events"]), len(payload["frames"]) * 3)
        self.assertEqual(len(payload["challenger_run"]["memory_event_ids"]), len(payload["evolution_events"]))
        self.assertEqual(payload["baseline_run"]["memory_event_ids"], [])

    def test_frame_trace_and_event_links_are_consistent(self):
        payload = self._payload()
        event_by_id = {event["id"]: event for event in payload["evolution_events"]}
        trace_by_frame_id = {trace["frame_id"]: trace for trace in payload["reasoning_traces"]}

        for frame in payload["frames"]:
            self.assertEqual(len(frame["memory_event_ids"]), 3)
            trace = trace_by_frame_id[frame["id"]]
            self.assertEqual(trace["memory_event_ids"], frame["memory_event_ids"])
            for event_id in frame["memory_event_ids"]:
                event = event_by_id[event_id]
                self.assertEqual(event["frame_id"], frame["id"])
                self.assertEqual(event["chosen_algorithm_id"], "autosolver_agent")
                self.assertEqual(event["secret_handling"], "env-only-redacted")
                self.assertTrue(event["context_signature"])
                self.assertTrue(event["learned_rule"])

    def test_writeback_and_future_policy_increase_confidence(self):
        payload = self._payload()
        writebacks = [event for event in payload["evolution_events"] if event["event_type"] == "memory_writeback"]
        policy_shifts = [event for event in payload["evolution_events"] if event["event_type"] == "future_policy_shift"]

        self.assertTrue(writebacks)
        self.assertTrue(policy_shifts)
        for event in writebacks[:10]:
            self.assertTrue(event["writeback"])
            self.assertGreater(event["confidence_after"], event["confidence_before"])
            self.assertIn("AutoSolver", event["learned_rule"])
        for event in policy_shifts[:10]:
            self.assertTrue(event["writeback"])
            self.assertGreater(event["confidence_after"], event["confidence_before"])
            self.assertIn("Future policy", event["learned_rule"])

    def test_predictor_falls_back_without_external_env(self):
        payload = self._payload(env={})
        predictor = payload["reasoning_traces"][0]["evidence"]["llm_predictor"]

        self.assertEqual(predictor["provider"], "local-heuristic")
        self.assertEqual(predictor["status"], "fallback")
        self.assertEqual(predictor["used_external_api"], False)
        self.assertEqual(predictor["secret_handling"], "env-only-redacted")
        self.assertEqual({item["algorithm_id"] for item in predictor["ranked_algorithms"]}, {"nearest_greedy", "autosolver_agent"})

    def test_predictor_env_hook_redacts_configured_values(self):
        secret_env = {
            "AUTOSOLVER_LLM_BASE_URL": "https://example.invalid/not-real",
            "AUTOSOLVER_LLM_API_KEY": "token-not-a-real-secret-value",
            "AUTOSOLVER_LLM_MODEL": "private-model-name",
        }
        payload = self._payload(env=secret_env)
        predictor = payload["reasoning_traces"][0]["evidence"]["llm_predictor"]
        serialized = json.dumps(payload, sort_keys=True)

        self.assertEqual(predictor["provider"], "external-env-hook")
        self.assertEqual(predictor["status"], "env-ready-fallback")
        self.assertEqual(predictor["model"], "env:AUTOSOLVER_LLM_MODEL")
        self.assertEqual(predictor["base_url"], "env:AUTOSOLVER_LLM_BASE_URL")
        self.assertEqual(predictor["used_external_api"], False)
        for secret_value in secret_env.values():
            self.assertNotIn(secret_value, serialized)

    def test_memory_mode_off_disables_evolution_events(self):
        payload = self._payload(memory_mode="off")

        self.assertEqual(payload["evolution_events"], [])
        self.assertTrue(all(frame["memory_event_ids"] == [] for frame in payload["frames"]))
        self.assertTrue(all(trace["memory_event_ids"] == [] for trace in payload["reasoning_traces"]))
        self.assertEqual(payload["challenger_run"]["memory_event_ids"], [])


if __name__ == "__main__":
    unittest.main()
