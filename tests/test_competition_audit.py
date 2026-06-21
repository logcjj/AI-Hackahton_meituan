import tempfile
import textwrap
import unittest
from pathlib import Path

from autosolver.competition_audit import (
    compare_solver_outputs,
    parse_competition_rows,
    result_metrics,
    solution_expected_cost,
)


SAMPLE_TEXT = """task_id_list\tcourier_id\ttotal_score\twillingness
T1\tC1\t10\t0.5
T1\tC2\t20\t0.5
T2\tC1\t7\t0.9
T2\tC3\t30\t0.2
T1,T2\tC4\t40\t0.8
"""


class CompetitionAuditTest(unittest.TestCase):
    def test_parse_rows_keeps_task_tuple_and_row_index(self):
        rows, tasks = parse_competition_rows(SAMPLE_TEXT)

        self.assertEqual(tasks, {"T1", "T2"})
        self.assertEqual(rows[("T1", "C1")].task_ids, ("T1",))
        self.assertEqual(rows[("T1,T2", "C4")].row_index, 4)

    def test_expected_cost_matches_acceptance_subset_formula(self):
        rows, tasks = parse_competition_rows(SAMPLE_TEXT)
        solution = [("T1", ["C1", "C2"]), ("T2", ["C3"])]

        # T1: none=0.25*100, C1-only=0.25*10, C2-only=0.25*20, both=0.25*15 => 36.25
        # T2: accept=0.2*30, none=0.8*100 => 86
        self.assertAlmostEqual(solution_expected_cost(solution, rows, tasks), 122.25)

    def test_result_metrics_reports_structure_and_invalidity(self):
        rows, tasks = parse_competition_rows(SAMPLE_TEXT)
        metrics = result_metrics([("T1,T2", ["C4"])], rows, tasks)

        self.assertEqual(metrics["covered_tasks"], 2)
        self.assertEqual(metrics["uncovered_tasks"], 0)
        self.assertEqual(metrics["tasks_per_group"], {2: 1})
        self.assertEqual(metrics["riders_per_group"], {1: 1})
        self.assertEqual(metrics["valid"], True)

    def test_compare_solver_outputs_detects_signature_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "base_solver.py"
            cand = Path(directory) / "candidate_solver.py"
            base.write_text("def solve(input_text):\n    return [('T1', ['C1']), ('T2', ['C3'])]\n")
            cand.write_text("def solve(input_text):\n    return [('T1,T2', ['C4'])]\n")

            comparison = compare_solver_outputs(base, cand, SAMPLE_TEXT)

        self.assertNotEqual(comparison["baseline"]["signature"], comparison["candidate"]["signature"])
        self.assertLess(comparison["candidate"]["expected_cost"], comparison["baseline"]["expected_cost"])
        self.assertEqual(comparison["delta_expected_cost"], comparison["candidate"]["expected_cost"] - comparison["baseline"]["expected_cost"])


if __name__ == "__main__":
    unittest.main()
