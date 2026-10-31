import unittest

from app.service import total


class T(unittest.TestCase):
    def test_total(self):
        self.assertEqual(total([{"price_cents": 100}, {"price_cents": 50}], 10), 165)
