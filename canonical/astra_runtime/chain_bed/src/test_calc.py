import unittest
from calc import compute_total


class TestTotal(unittest.TestCase):
    def test_doubled_total(self):
        self.assertEqual(compute_total([1, 2, 3]), 12)
