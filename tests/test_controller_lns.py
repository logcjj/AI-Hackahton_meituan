import unittest

from autosolver.candidate_gen import generate_candidates
from autosolver.controller import solve as controller_solve
from autosolver.fast_evaluator import fast_evaluate
from autosolver.greedy import greedy_marginal
from autosolver.models import Instance, Order, Rider, Weights
from autosolver.objective import objective


class ControllerLnsTest(unittest.TestCase):
    def test_controller_never_returns_worse_than_baseline(self):
        instance = Instance(
            id='c',
            orders=[Order(id='O1'), Order(id='O2', pickup=(0.1, 0)), Order(id='O3', pickup=(5, 0), score=15)],
            riders=[Rider(id='R1'), Rider(id='R2'), Rider(id='R3')],
            p=[[0.7, 0.5, 0.1], [0.6, 0.6, 0.1], [0.1, 0.2, 0.8]],
            weights=Weights(),
        )
        candidates = generate_candidates(instance)
        baseline = greedy_marginal(candidates, instance)

        improved, trace = controller_solve(instance, candidates, baseline, remaining_time=1.0, debug=True)

        self.assertGreaterEqual(objective(fast_evaluate(improved, instance), instance), objective(fast_evaluate(baseline, instance), instance))
        self.assertIn('events', trace)


if __name__ == '__main__':
    unittest.main()
