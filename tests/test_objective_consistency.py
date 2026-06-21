import unittest

from autosolver.models import EvalResult, Instance, Weights
from autosolver.objective import better, objective


class ObjectiveConsistencyTest(unittest.TestCase):
    def test_objective_reward_and_cost_share_single_formula(self):
        reward_instance = Instance(id='x', orders=[], riders=[], p=[], weights=Weights(expected_accepts=1.0, score=0.5), score_direction='reward')
        cost_instance = Instance(id='x', orders=[], riders=[], p=[], weights=Weights(expected_accepts=1.0, score=0.5), score_direction='cost')
        result = EvalResult(feasible=True, expected_accepts=2.0, total_score=10.0, per_order_p={})
        self.assertEqual(objective(result, reward_instance), 7.0)
        self.assertEqual(objective(result, cost_instance), -3.0)

    def test_better_rejects_infeasible_even_with_high_score(self):
        instance = Instance(id='x', orders=[], riders=[], p=[], weights=Weights())
        feasible = EvalResult(feasible=True, expected_accepts=1.0, total_score=1.0, per_order_p={})
        infeasible = EvalResult(feasible=False, expected_accepts=100.0, total_score=100.0, per_order_p={})
        self.assertTrue(better(feasible, infeasible, instance))


if __name__ == '__main__':
    unittest.main()
