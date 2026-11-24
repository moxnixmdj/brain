#!/usr/bin/env python3
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import unittest
import canonical.swe_kernel.verified_skill_crystallizer_ir_bridge_v1 as br

class IRBridgeTests(unittest.TestCase):
    def test_for_while_same_hash(self):
        h1 = br.canonical_hash("for i in range(n):\n    x += 1", "python")
        h2 = br.canonical_hash("i = 0\nwhile i < n:\n    x += 1\n    i += 1", "python")
        self.assertEqual(h1, h2, "for-range and while-counter must be same Loop IR")

    def test_alpha_rename(self):
        h_i = br.canonical_hash("for i in range(n):\n    x+=1")
        h_j = br.canonical_hash("for j in range(n):\n    x+=1")
        self.assertEqual(h_i, h_j)

    def test_different_semantics_different_hash(self):
        h1 = br.canonical_hash("for i in range(n):\n    x+=1")
        h2 = br.canonical_hash("for i in range(n):\n    x+=2")
        self.assertNotEqual(h1, h2)

    def test_enrich_and_match(self):
        rule = br.crystallize_with_ir(before_snippet="for i in range(n):\n    x += 1", after_snippet="for i in range(n):\n    x += 2")
        self.assertIsNotNone(rule)
        self.assertIn("ir_hash_before", rule)
        # same meaning but different var name should match via IR
        self.assertTrue(br.ir_matches(rule, "for j in range(n):\n    x += 1"))
        # different semantics should not match
        self.assertFalse(br.ir_matches(rule, "x = 1"))

    def test_c_for_normalized(self):
        h = br.canonical_hash("for (int i=0; i<n; i++) { x++; }", "c")
        self.assertIn("Loop", str(br.canonical_ir("for (int i=0; i<n; i++) { x++; }", "c")))

    def test_for_while_demo_equal(self):
        res = br.for_while_same_ir()
        self.assertTrue(res["equal"])

if __name__ == "__main__":
    unittest.main()
