import unittest

from autosolver.formatter import format_solution
from autosolver.models import AssignmentCandidate, Instance, Order, Rider, Weights
from autosolver.validator import validate


class ValidatorTest(unittest.TestCase):
    def test_validator_rejects_duplicate_order_in_assignment_and_bad_ids(self):
        instance = Instance(id='v', orders=[Order(id='O1')], riders=[Rider(id='R1')], p=[[0.8]], weights=Weights())
        output = {'assignments': [{'order_id': 'BAD', 'rider_ids': ['R2', 'R2']}], 'rejected': []}

        violations = validate(output, instance)

        self.assertTrue(any('unknown order' in item for item in violations))
        self.assertTrue(any('unknown rider' in item for item in violations))
        self.assertTrue(any('duplicate pair' in item for item in violations))

    def test_formatter_and_validator_accept_valid_bundle_multidispatch(self):
        order = Order(id='O1')
        riders = [Rider(id='R1'), Rider(id='R2')]
        instance = Instance(id='v', orders=[order], riders=riders, p=[[0.8, 0.7]], weights=Weights())
        solution = [
            AssignmentCandidate(order_ids=['O1'], rider=riders[0], probability=0.8, score=10, is_bundle=True),
            AssignmentCandidate(order_ids=['O1'], rider=riders[1], probability=0.7, score=10, is_bundle=False),
        ]

        output = format_solution(solution, instance)

        self.assertEqual(validate(output, instance), [])
        self.assertTrue(output['assignments'][0]['is_bundle'])
        self.assertTrue(output['assignments'][0]['is_multi_dispatch'])


if __name__ == '__main__':
    unittest.main()
