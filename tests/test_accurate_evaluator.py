import unittest

from autosolver.accurate_evaluator import accurate_evaluate
from autosolver.models import AssignmentCandidate, Instance, Order, Rider, Weights


class AccurateEvaluatorTest(unittest.TestCase):
    def test_accurate_evaluate_is_reproducible_and_close_to_closed_form(self):
        order = Order(id='O1')
        riders = [Rider(id='R1'), Rider(id='R2')]
        instance = Instance(id='sim', orders=[order], riders=riders, p=[[0.5, 0.5]], weights=Weights())
        solution = [
            AssignmentCandidate(order_ids=['O1'], rider=riders[0], probability=0.5, score=10),
            AssignmentCandidate(order_ids=['O1'], rider=riders[1], probability=0.5, score=10),
        ]

        first = accurate_evaluate(solution, instance, n_simulations=2000)
        second = accurate_evaluate(solution, instance, n_simulations=2000)

        self.assertEqual(first.per_order_p, second.per_order_p)
        self.assertAlmostEqual(first.expected_accepts, 0.75, delta=0.05)


if __name__ == '__main__':
    unittest.main()
