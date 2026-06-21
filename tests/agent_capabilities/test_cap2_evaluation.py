from __future__ import annotations

import unittest

from tests.agent_capabilities._trace_fixture import large_trace


class EvaluationCapabilityTest(unittest.TestCase):
    def test_trace_records_critic_evaluations_and_valid_proxy(self):
        trace = large_trace()
        solution = trace["solution"]

        self.assertGreater(trace["summary"]["critic_evaluations"], 0)
        self.assertTrue(solution["valid"], solution["invalid_reasons"])
        self.assertLess(solution["proxy_score"], 700.0)
        self.assertEqual(solution["covered_tasks"], solution["total_tasks"])


if __name__ == "__main__":
    unittest.main()
