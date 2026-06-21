import unittest

from autosolver.fallback import FallbackChain
from autosolver.models import Instance, Order, Rider, Weights


class FallbackTest(unittest.TestCase):
    def test_fallback_1_does_not_assign_same_rider_to_conflicting_orders(self):
        orders = [
            Order(id='O1', pickup=(0, 0), dropoff=(1, 0), ready_time=0, due_time=10),
            Order(id='O2', pickup=(0, 0), dropoff=(1, 0), ready_time=1, due_time=11),
        ]
        riders = [Rider(id='R1'), Rider(id='R2')]
        instance = Instance(id='case', orders=orders, riders=riders, p=[[0.9, 0.2], [0.8, 0.7]], weights=Weights())

        solution = FallbackChain().fallback_1_top_p(instance)

        self.assertEqual(len(solution), 2)
        assignments = {(candidate.order_ids[0], candidate.rider.id) for candidate in solution}
        self.assertEqual(assignments, {('O1', 'R1'), ('O2', 'R2')})


if __name__ == '__main__':
    unittest.main()
