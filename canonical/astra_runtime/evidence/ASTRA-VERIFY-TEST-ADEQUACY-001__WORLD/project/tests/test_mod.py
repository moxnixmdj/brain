import unittest

from app.mod import covered


class T(unittest.TestCase):
    def test_covered(self):
        self.assertEqual(covered(1), 2)
