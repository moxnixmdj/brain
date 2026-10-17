import unittest
from core import add, mul, join_tags

class T(unittest.TestCase):
    def test_add(self): self.assertEqual(add(2, 3), 5)
    def test_mul(self): self.assertEqual(mul(4, 5), 20)
    def test_tags(self): self.assertEqual(join_tags(["a", "b"]), "a,b")
if __name__ == "__main__":
    unittest.main()
