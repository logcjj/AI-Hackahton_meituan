import unittest

from autosolver.candidate_gen import generate_candidates
from autosolver.models import Instance, Order, Rider, Weights


class CandidateGenerationTest(unittest.TestCase):
    def test_bundle_candidates_use_bundle_base_probability_top_k_not_rider_prefix(self):
        orders = [
            Order(id=0, pickup=(0, 0), dropoff=(1, 0), ready_time=0, due_time=20),
            Order(id=1, pickup=(0.1, 0), dropoff=(1.1, 0), ready_time=0, due_time=20),
        ]
        riders = [Rider(id=f'R{i}') for i in range(20)]
        p = [[0.01 for _ in range(20)] for _ in range(2)]
        p[0][19] = 0.95
        p[1][19] = 0.94
        instance = Instance(id='bundle', orders=orders, riders=riders, p=p, weights=Weights())

        candidates = generate_candidates(instance, time_budget=1.0)

        bundle_riders = {candidate.rider.id for candidate in candidates if candidate.is_bundle}
        self.assertIn('R19', bundle_riders)


if __name__ == '__main__':
    unittest.main()
