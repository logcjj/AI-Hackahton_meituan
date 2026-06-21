import unittest

from autosolver.candidate_gen import make_single_candidate
from autosolver.greedy import greedy_marginal
from autosolver.models import Instance, Order, Rider, Weights
from autosolver.validator import validate
from autosolver.formatter import format_solution


class GreedyStateTest(unittest.TestCase):
    def test_greedy_repair_respects_initial_solution_rider_conflicts(self):
        orders = [
            Order(id='O1', ready_time=0, due_time=10),
            Order(id='O2', ready_time=1, due_time=11),
        ]
        rider = Rider(id='R1')
        instance = Instance(id='g', orders=orders, riders=[rider], p=[[0.9], [0.8]], weights=Weights())
        initial = [make_single_candidate(orders[0], rider, instance)]
        pool = [make_single_candidate(orders[1], rider, instance)]

        solution = greedy_marginal(pool, instance, initial_solution=initial)

        self.assertEqual([candidate.order_ids for candidate in solution], [['O1']])
        self.assertEqual(validate(format_solution(solution, instance), instance), [])


if __name__ == '__main__':
    unittest.main()
