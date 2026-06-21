import unittest

from autosolver.competition import (
    parse_candidates,
    solution_metrics,
    solve,
    solve_candidates,
    validate_competition_solution,
)
from autosolver.submission import run


SAMPLE_TEXT = """task_id_list\tcourier_id\ttotal_score\twillingness
T1\tC1\t10\t0.1
T1\tC2\t8\t0.2
T2\tC1\t9\t0.3
T2\tC3\t7\t0.4
T1,T2\tC4\t12\t0.8
"""


class CompetitionSolverTest(unittest.TestCase):
    def test_parse_candidates_reads_tsv_rows(self):
        candidates = parse_candidates(SAMPLE_TEXT)

        self.assertEqual(len(candidates), 5)
        self.assertEqual(candidates[-1].task_ids, ("T1", "T2"))
        self.assertEqual(candidates[-1].courier_id, "C4")

    def test_solver_returns_judge_shape_without_conflicts(self):
        output = solve(SAMPLE_TEXT)

        self.assertEqual(output, [("T1", ["C2"]), ("T1,T2", ["C4"]), ("T2", ["C3"])])

    def test_solve_candidates_allows_multidispatch_and_uses_bundle(self):
        candidates = parse_candidates(SAMPLE_TEXT)
        solution = solve_candidates(candidates)

        self.assertEqual(validate_competition_solution(solution), [])
        self.assertEqual(solution_metrics(solution)["covered_tasks"], 2.0)
        self.assertAlmostEqual(solution_metrics(solution)["expected_accepts"], 1.72)
        self.assertEqual(solution_metrics(solution)["total_score"], 27.0)

    def test_submission_run_dispatches_string_input_to_competition_solver(self):
        self.assertEqual(run(SAMPLE_TEXT), [("T1", ["C2"]), ("T1,T2", ["C4"]), ("T2", ["C3"])])


if __name__ == "__main__":
    unittest.main()
