import unittest

from app.models import Item


class T(unittest.TestCase):
    def test_total(self):
        self.assertEqual(Item(100, 2).total(), 200)
