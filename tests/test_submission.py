import unittest

from autosolver.submission import run


class SubmissionTest(unittest.TestCase):
    def test_run_is_clean_submit_api(self):
        output = run({'id': 's', 'orders': [{'id': 'O1'}], 'riders': [{'id': 'R1'}], 'p_matrix': [[0.8]]}, time_budget=1.0)
        self.assertEqual(set(output), {'assignments', 'rejected'})


if __name__ == '__main__':
    unittest.main()
