from __future__ import annotations

import unittest

from tests.agent_capabilities._trace_fixture import large_trace


class ExplorationCapabilityTest(unittest.TestCase):
    def test_large_case_explores_multiple_solver_strategies(self):
        trace = large_trace()
        strategy_calls = trace["summary"]["strategy_calls"]
        available = trace["summary"]["available_strategy_functions"]

        self.assertEqual(trace["regime"], "large")
        self.assertGreaterEqual(len(available), 3)
        self.assertGreaterEqual(len(strategy_calls), 2)
        self.assertIn("_solve_single_task_multidispatch", strategy_calls)


if __name__ == "__main__":
    unittest.main()
