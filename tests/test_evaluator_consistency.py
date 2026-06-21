import unittest

from autosolver.fast_evaluator import fast_evaluate
from autosolver.models import AssignmentCandidate, Instance, Order, Rider, Weights


class EvaluatorConsistencyTest(unittest.TestCase):
    def test_multi_dispatch_order_probability_uses_independent_union(self):
        order = Order(id='O1')
        riders = [Rider(id='R1'), Rider(id='R2')]
        instance = Instance(id='eval', orders=[order], riders=riders, p=[[0.5, 0.5]], weights=Weights())
        solution = [
            AssignmentCandidate(order_ids=['O1'], rider=riders[0], probability=0.5, score=10),
            AssignmentCandidate(order_ids=['O1'], rider=riders[1], probability=0.5, score=10),
        ]

        result = fast_evaluate(solution, instance)

        self.assertTrue(result.feasible)
        self.assertEqual(result.per_order_p['O1'], 0.75)
        self.assertEqual(result.expected_accepts, 0.75)


if __name__ == '__main__':
    unittest.main()
