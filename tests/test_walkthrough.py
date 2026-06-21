import unittest

from autosolver.walkthrough import walkthrough_expected_accepts


class WalkthroughTest(unittest.TestCase):
    def test_walkthrough_expected_accepts_matches_v5_baseline(self):
        self.assertEqual(walkthrough_expected_accepts(), 1.94)


if __name__ == '__main__':
    unittest.main()
