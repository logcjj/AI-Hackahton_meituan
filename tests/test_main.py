import unittest

from autosolver.main import solve


class MainSolveTest(unittest.TestCase):
    def test_solve_adapter_failure_returns_raw_emergency_output(self):
        raw = {'orders': [{'order_id': 'O1'}, {'id': 'O2'}], 'force_adapter_error': True}
        self.assertEqual(solve(raw), {'assignments': [], 'rejected': ['O1', 'O2']})


if __name__ == '__main__':
    unittest.main()
