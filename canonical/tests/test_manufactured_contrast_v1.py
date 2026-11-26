"""Pure checks for one-literal counterfactual generation."""
import pathlib
import sys
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "swe_kernel"))

import manufactured_contrast_v1 as mc  # noqa: E402

SOURCE = textwrap.dedent('''
    def test_case():
        value = "abc"
        assert value == "abc"
''')


class ManufacturedContrastTests(unittest.TestCase):
    def test_literals_are_located_in_the_named_function(self):
        holes = mc.literals(SOURCE, "test_case")
        self.assertEqual([hole["value"] for hole in holes], ["abc"])
        self.assertEqual([hole["role"] for hole in holes], ["input"])

    def test_single_character_mutations_are_generated(self):
        hole = {"value": "ab", "line": 1, "col": 0, "end_col": 4}
        found = [value for value, how in mc.mutations(hole, ["c"]) if value == "ac"]
        self.assertIn("ac", found)
        self.assertNotIn("", [value for value, _ in found])

    def test_truthiness_flips_are_not_offered(self):
        values = [value for value, _ in mc.mutations({"value": 1, "line": 1,
                                                       "col": 0, "end_col": 1}, ["0"])]
        self.assertNotIn(0, values)

    def test_patch_only_changes_the_literal_span(self):
        hole = mc.literals(SOURCE, "test_case")[0]
        patched = mc.patch_literal(SOURCE, hole, "abd")
        self.assertIn("value = 'abd'", patched)
        self.assertIn('assert value == "abc"', patched)


if __name__ == "__main__":
    unittest.main()


class TraceContrastTests(unittest.TestCase):
    def test_trace_returns_the_executed_source_lines(self):
        with tempfile.TemporaryDirectory() as where:
            root = pathlib.Path(where)
            repo = root / "repo"
            repo.mkdir()
            (repo / "mod.py").write_text(
                "def check(value):\n    result = value + 1\n    return result > 2\n",
                encoding="utf-8",
            )
            (repo / "test_mod.py").write_text(
                "from mod import check\n\ndef test_case():\n    assert check(2) is True\n",
                encoding="utf-8",
            )
            lines = mc.trace_lines(repo, "test_mod.py::test_case", "mod.py",
                                   root / "trace", 20)
            self.assertIsNotNone(lines)
            self.assertIn(2, lines)
