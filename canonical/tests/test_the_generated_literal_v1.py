"""Unit checks for the two fresh-corpus falsifiers. No model, no network, no repo clone."""
import ast
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))

import the_constant_is_a_hole_v1 as hole  # noqa: E402
import the_replacement_expression_v1 as expr  # noqa: E402


class ReplacementExpressionTests(unittest.TestCase):
    def test_logged_unknown_is_not_content_addressable(self):
        row = {"operands": {"x": "<marshmallow.fields.Field object at 0x1>"}}
        self.assertIsNone(expr.evaluate("x == 3", row))
        self.assertTrue(expr.evaluate("x is not None", row))

    def test_length_atom_is_generated_from_the_run(self):
        site = {"operands": ["x"]}
        rows = [{"n": 1, "truth": True, "operands": {"x": "[1, 2]"}},
                {"n": 2, "truth": True, "operands": {"x": "[]"}}]
        self.assertIn("len(x) == 2", expr.candidate_expressions(site, rows))
        fit = expr.fit_replacement(site, rows, 2)
        self.assertIsNotNone(fit)
        self.assertIs(expr.evaluate(fit["predicate"], rows[0]), True)
        self.assertIs(expr.evaluate(fit["predicate"], rows[1]), False)
        self.assertEqual(fit["false_at"], 2)

    def test_vacuous_fit_is_refused(self):
        site = {"operands": ["x"]}
        rows = [{"n": 1, "truth": True, "operands": {"x": "None"}}]
        self.assertIsNone(expr.fit_replacement(site, rows, 1))

    def test_hand_written_markers_are_not_counted_as_novel(self):
        for text in ("x is not None", "(x is None)", "not x"):
            self.assertTrue(expr.is_hand_written(text))


class ConstantHoleTests(unittest.TestCase):
    def test_class_insertion_produces_the_unseen_character(self):
        source = 'relative_part = r"(?:/?|[/?]\\\\S+)\\\\Z"'
        tree = ast.parse(source)
        h = hole.literals(tree)[0]
        candidates = [value for value, how in hole.mutations(h, ["#"]) if how == "class+'#'"]
        self.assertIn("(?:/?|[/?#]\\\\S+)\\\\Z", candidates)

    def test_patch_edits_only_the_literal_span(self):
        source = "value = 3  # keep this\n"
        h = hole.literals(ast.parse(source))[0]
        self.assertEqual(hole.patch(source, h, 4), "value = 4  # keep this\n")

    def test_ranking_prefers_the_failing_input_character(self):
        h = {"value": "[/?]"}
        score_hash = hole.score(h, "[/?#]", ["http://example.org#fragment"], ["x"], "class+'#'")
        score_other = hole.score(h, "[/?x]", ["http://example.org#fragment"], ["x"], "class+'x'")
        self.assertGreater(score_hash, score_other)

    def test_diff_is_not_read_by_the_generator(self):
        text = (ROOT / "canonical" / "tools" / "the_constant_is_a_hole_v1.py").read_text()
        self.assertNotIn('identify.show(repo, sha, source_path)', text)
        self.assertNotIn("diff --", text)


if __name__ == "__main__":
    unittest.main()
