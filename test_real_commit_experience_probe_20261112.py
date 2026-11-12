"""Regression checks for the real-commit probe's local structural oracle."""
import tempfile
import unittest
from pathlib import Path

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as learner
from real_commit_experience_probe_20261112 import digest, require_hash, verify_candidate, wrong_applicability


class OracleTests(unittest.TestCase):
    def setUp(self):
        self.before = "def check(self, value):\n    self.assertRegexpMatches(value, 'a')\n"

    def test_accepts_only_intended_rewrite_ignoring_formatting(self):
        candidate = "def check(self,value):\n self.assertRegex(value, 'a')\n"
        result = verify_candidate(self.before, candidate)
        self.assertTrue(result["matches_expected_ast"])
        self.assertEqual(result["applicable_sites"], 1)
        self.assertEqual(result["remaining_old_sites"], 0)

    def test_rejects_unchanged_and_unrelated_changes(self):
        self.assertFalse(verify_candidate(self.before, self.before)["matches_expected_ast"])
        altered = self.before.replace("assertRegexpMatches", "assertRegex").replace("'a'", "'b'")
        self.assertFalse(verify_candidate(self.before, altered)["matches_expected_ast"])

    def test_rejects_no_site_and_invalid_python(self):
        self.assertFalse(verify_candidate("x = 1\n", "x = 1\n")["matches_expected_ast"])
        self.assertFalse(verify_candidate(self.before, "def broken(")["matches_expected_ast"])

    def test_only_self_method_is_within_scope(self):
        original = self.before + "def other(obj):\n    obj.assertRegexpMatches('x', 'a')\n"
        candidate = original.replace("self.assertRegexpMatches", "self.assertRegex")
        self.assertTrue(verify_candidate(original, candidate)["matches_expected_ast"])
        all_replaced = original.replace("assertRegexpMatches", "assertRegex")
        self.assertFalse(verify_candidate(original, all_replaced)["matches_expected_ast"])

    def test_wrong_applicability_detects_behavioral_regression(self):
        before = "def f(self):\n    self.assertRegexpMatches('a', 'b', 'c')\n"
        after = before.replace("assertRegexpMatches", "assertRegex")
        outcome = wrong_applicability(learner.learn_all([(before, after)]))
        self.assertTrue(outcome["no_memory"]["preserves_behavior"])
        self.assertFalse(outcome["hand_adapted_raw"]["preserves_behavior"])
        self.assertFalse(outcome["one_demo_strict"]["preserves_behavior"])

    def test_hash_gate_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.py"
            path.write_text("x = 1\n", encoding="utf-8")
            require_hash(path, digest(path))
            with self.assertRaises(ValueError):
                require_hash(path, "0" * 64)
            with self.assertRaises(ValueError):
                require_hash(path.parent / "missing.py", "0" * 64)


if __name__ == "__main__":
    unittest.main()
