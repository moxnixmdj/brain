import unittest
from util import twice


class CalcTests(unittest.TestCase):
    def test_twice_uses_add(self):
        self.assertEqual(twice(2, 3), 10)


if __name__ == "__main__":
    unittest.main()
