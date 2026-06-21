import unittest

from autosolver.analyzer import summarize_candidates, summarize_instance
from autosolver.candidate_gen import generate_candidates
from autosolver.column_solver import solve_columns
from autosolver.config import load_config
from autosolver.fast_evaluator import fast_evaluate
from autosolver.greedy import greedy_marginal
from autosolver.models import Instance, Order, Rider, Weights
from autosolver.objective import objective
from autosolver.strategies import choose_strategy


class ConfigAnalyzerColumnTest(unittest.TestCase):
    def test_load_config_reads_yaml_subset(self):
        config = load_config('autosolver/config.yaml')
        self.assertEqual(config['objective']['weight_expected_accepts'], 1.0)
        self.assertEqual(config['score_direction'], 'reward')

    def test_analyzer_summarizes_instance_and_candidates(self):
        instance = Instance(id='a', orders=[Order(id='O1'), Order(id='O2', pickup=(0.1, 0))], riders=[Rider(id='R1')], p=[[0.8], [0.7]], weights=Weights())
        candidates = generate_candidates(instance)

        self.assertEqual(summarize_instance(instance)['orders'], 2)
        self.assertGreaterEqual(summarize_candidates(candidates)['bundle_candidates'], 1)

    def test_column_solver_matches_or_beats_greedy_on_small_case(self):
        instance = Instance(id='col', orders=[Order(id='O1'), Order(id='O2', pickup=(0.1, 0))], riders=[Rider(id='R1'), Rider(id='R2')], p=[[0.9, 0.6], [0.8, 0.7]], weights=Weights())
        candidates = generate_candidates(instance)
        greedy = greedy_marginal(candidates, instance)
        columns = solve_columns(candidates, instance, time_budget=1.0)

        self.assertGreaterEqual(objective(fast_evaluate(columns, instance), instance), objective(fast_evaluate(greedy, instance), instance))

    def test_strategy_router_uses_instance_size_and_time(self):
        small = Instance(id='s', orders=[Order(id='O1')], riders=[Rider(id='R1')], p=[[0.8]], weights=Weights())
        large = Instance(id='l', orders=[Order(id=f'O{i}') for i in range(200)], riders=[Rider(id='R1')], p=[[0.8] for _ in range(200)], weights=Weights())
        self.assertEqual(choose_strategy(small, time_budget=10), 'column_then_lns')
        self.assertEqual(choose_strategy(large, time_budget=1), 'greedy_only')


if __name__ == '__main__':
    unittest.main()
