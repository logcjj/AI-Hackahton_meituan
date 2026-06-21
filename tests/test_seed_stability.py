import unittest

from autosolver.models import Instance, Weights
from autosolver.utils.seed import get_seed, stable_hash


class SeedStabilityTest(unittest.TestCase):
    def test_stable_hash_is_deterministic(self):
        self.assertEqual(stable_hash('case-1::lns'), stable_hash('case-1::lns'))
        self.assertNotEqual(stable_hash('case-1::lns'), stable_hash('case-1::greedy'))

    def test_get_seed_uses_instance_id_and_module(self):
        instance = Instance(id='case-1', orders=[], riders=[], p=[], weights=Weights())
        self.assertEqual(get_seed(instance, 'lns'), stable_hash('case-1::lns'))


if __name__ == '__main__':
    unittest.main()
