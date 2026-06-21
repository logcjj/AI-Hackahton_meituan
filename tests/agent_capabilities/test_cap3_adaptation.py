from __future__ import annotations

import unittest

from tests.agent_capabilities._trace_fixture import large_trace


class AdaptationCapabilityTest(unittest.TestCase):
    def test_trace_records_iterative_improvement_functions(self):
        trace = large_trace()
        improver_calls = trace["summary"]["improver_calls"]
        available = trace["summary"]["available_improver_functions"]

        self.assertIn("_local_improve_mixed_solution", available)
        self.assertGreaterEqual(sum(improver_calls.values()), 1)


if __name__ == "__main__":
    unittest.main()
