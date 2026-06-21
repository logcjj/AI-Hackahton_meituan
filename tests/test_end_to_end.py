import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from autosolver.adapter import adapt
from autosolver.main import solve
from autosolver.validator import validate


SAMPLE_INPUT = {
    'id': 'walkthrough',
    'orders': [
        {'id': 'O1', 'pickup': [0, 0], 'dropoff': [1, 0], 'ready_time': 0, 'due_time': 20, 'score': 10},
        {'id': 'O2', 'pickup': [0.1, 0], 'dropoff': [1.1, 0], 'ready_time': 0, 'due_time': 20, 'score': 10},
        {'id': 'O3', 'pickup': [10, 0], 'dropoff': [11, 0], 'ready_time': 0, 'due_time': 20, 'score': 15},
    ],
    'riders': [{'id': 'R1'}, {'id': 'R2'}, {'id': 'R3'}],
    'p_matrix': [[0.7, 0.5, 0.1], [0.6, 0.6, 0.1], [0.1, 0.2, 0.8]],
    'score_direction': 'reward',
    'weights': {'expected_accepts': 1.0, 'score': 0.5},
}


class EndToEndTest(unittest.TestCase):
    def test_solve_returns_submit_clean_legal_output(self):
        output = solve(SAMPLE_INPUT, time_budget=2.0, debug=False)

        self.assertEqual(set(output), {'assignments', 'rejected'})
        assigned = {assignment['order_id'] for assignment in output['assignments']}
        rejected = set(output['rejected'])
        self.assertEqual(assigned | rejected, {'O1', 'O2', 'O3'})
        self.assertFalse(assigned & rejected)
        self.assertEqual(validate(output, adapt(SAMPLE_INPUT)), [])

    def test_debug_mode_contains_debug_without_breaking_output(self):
        output = solve(SAMPLE_INPUT, time_budget=2.0, debug=True)

        self.assertIn('debug', output)
        self.assertIn('assignments', output)
        self.assertIn('rejected', output)

    def test_cli_reads_json_and_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / 'input.json'
            output_path = Path(tmpdir) / 'output.json'
            input_path.write_text(json.dumps(SAMPLE_INPUT), encoding='utf-8')

            result = subprocess.run(
                [sys.executable, '-m', 'autosolver.main', '--input', str(input_path), '--output', str(output_path), '--time-budget', '2'],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(output_path.read_text(encoding='utf-8'))
            self.assertIn('assignments', output)
            self.assertIn('rejected', output)


if __name__ == '__main__':
    unittest.main()
