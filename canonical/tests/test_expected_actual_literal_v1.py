"""Pure checks for expected/actual literal surgery."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import expected_actual_literal_v1 as eal  # noqa: E402


class ExpectedActualLiteralTests(unittest.TestCase):
    def test_difference_is_computed_from_both_values(self):
        diffs = eal.differences("abc", "a#bc")
        self.assertIn(("", "#"), diffs)

    def test_literal_eval_handles_repr_values(self):
        self.assertEqual(eal.value_of("'a\\nb'"), "a\nb")
        self.assertIsNone(eal.value_of("not a literal"))

    def test_candidate_patch_changes_only_the_literal(self):
        source = "PATTERN = 'abc'\n"
        holes = eal.literal_holes(source, [1])
        out = eal.candidates(source, holes, [("abc", "ab#c")])
        self.assertTrue(out)
        patched, _ = out[0]
        self.assertIn("PATTERN = ", patched)
        self.assertNotEqual(patched, source)


if __name__ == "__main__":
    unittest.main()
