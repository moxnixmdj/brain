"""Insertion edits: the one fix shape the node diff could not see at all.

Measured blindness this pins (V23). `hasattr(x, 'c')` -> `getattr(x, 'c', None)` was demonstrated to
the basis and came back as two things:

  * a LITERAL template on `Name`: `hasattr` -> `getattr`, context `('Call',)` -- the callee rename,
    which travels nowhere useful, because applied anywhere it turns a guard into an AttributeError;
  * a NON_EXECUTABLE row `Call.args`, which can never be applied.

The repair itself -- the argument that has to APPEAR -- was in neither. The reason is structural:
`_sites` walks paths of the defective tree, so a node that exists only in the repaired tree has no
path, is never visited, and an insertion cannot be a difference. The insertion rung promotes the
differing position to the smallest enclosing node whose field LENGTH changed and makes that node the
pattern, so the added child is inside the pattern.

The tests below hold both halves of the claim: that the old rungs still miss the edit, and that the
new rung produces an edit whose behaviour can be judged by executing it somewhere else.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import textwrap
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.swe_kernel import induced_edit_basis_v1 as basis  # noqa: E402


def code(text: str) -> str:
    return textwrap.dedent(text).strip() + "\n"


DEFECTIVE = code(
    """
    def last(iterable, default=_marker):
        if isinstance(iterable, Sequence):
            return iterable[-1]
        if hasattr(iterable, '__reversed__'):
            return next(reversed(iterable))
        return deque(iterable, maxlen=1)[-1]
    """
)
REPAIRED = DEFECTIVE.replace("hasattr(iterable, '__reversed__')",
                             "getattr(iterable, '__reversed__', None)")


class TheBlindnessIsReal(unittest.TestCase):
    def test_node_diff_never_offers_the_inserted_argument(self):
        """No template from the node diff can add an argument -- the repair is unreachable."""
        for template in basis.induce_node_templates([("last", DEFECTIVE, REPAIRED)]):
            self.assertNotIn("None", template.new_pattern)
            self.assertNotIn("getattr(", template.old_pattern)

    def test_leaf_basis_classifies_the_repair_as_non_executable(self):
        templates = basis.induce_templates([("last", DEFECTIVE, REPAIRED)])
        call_rows = [t for t in templates if t.node_type == "Call" and t.role == "args"]
        self.assertEqual(len(call_rows), 1)
        self.assertFalse(call_rows[0].executable)

    def test_renaming_alone_regresses_at_a_held_out_site(self):
        """The reachable half of the lesson is not harmless: it removes the guard.

        `hasattr(x, 'seekable')` is False where the attribute is missing; `getattr(x, 'seekable')`
        raises. This is the measured reason a rename-only transfer was refused, not a matter of taste.
        """
        template = basis.induce_node_templates([("last", DEFECTIVE, REPAIRED)])[0]
        site = code("if hasattr(stream, 'seekable'):\n    return stream.seekable()")
        patches = basis.candidates_from_node_templates(site, [template])
        self.assertEqual(len(patches), 1)

        class Absent:
            def __getattr__(self, name):
                raise AttributeError(name)

        class Present:
            def __getattr__(self, name):
                return object()

        def truth(expression, witness):
            try:
                return bool(eval(expression, {"hasattr": hasattr, "getattr": getattr},
                                 {"x": witness}))
            except AttributeError:
                return "AttributeError"

        self.assertIs(truth("hasattr(x, 'seekable')", Absent()), False)
        self.assertIs(truth("getattr(x, 'seekable')", Absent()), "AttributeError")
        self.assertIs(truth("hasattr(x, 'seekable')", Present()), True)
        self.assertIs(truth("getattr(x, 'seekable')", Present()), True)


class TheInsertionRung(unittest.TestCase):
    def test_the_inserted_argument_is_part_of_a_generalized_pattern(self):
        templates = basis.induce_insertion_templates([("last", DEFECTIVE, REPAIRED)])
        relational = [t for t in templates if t.kind == "RELATIONAL"]
        self.assertEqual(len(relational), 1)
        template = relational[0]
        self.assertEqual(template.root_type, "Call")
        # both untouched subterms became holes; the inserted literal did not
        self.assertEqual(template.old_pattern,
                         f"hasattr({basis.HOLE_PREFIX}0__, {basis.HOLE_PREFIX}1__)")
        self.assertEqual(template.new_pattern,
                         f"getattr({basis.HOLE_PREFIX}0__, {basis.HOLE_PREFIX}1__, None)")

    def test_concrete_mode_keeps_the_demonstrations_literals(self):
        template = basis.induce_insertion_templates(
            [("last", DEFECTIVE, REPAIRED)], abstract_untouched=False)[0]
        self.assertEqual(template.kind, "LITERAL")
        self.assertEqual(template.old_pattern, "hasattr(iterable, '__reversed__')")
        self.assertEqual(template.new_pattern, "getattr(iterable, '__reversed__', None)")

    def test_removal_is_promoted_by_the_same_rule(self):
        """The rung is about field LENGTH, so a deletion is the same shape as an insertion."""
        before = code("def f(a, b):\n    return g(a, b)")
        after = code("def f(a, b):\n    return g(a)")
        templates = basis.induce_insertion_templates([("f", before, after)])
        self.assertEqual(len(templates), 1)
        self.assertIn(basis.HOLE_PREFIX, templates[0].old_pattern)
        self.assertNotEqual(templates[0].old_pattern, templates[0].new_pattern)

    def test_transferred_edit_changes_only_the_none_valued_class(self):
        """Judge the transfer by execution at a site the demonstration never saw."""
        template = [t for t in basis.induce_insertion_templates([("last", DEFECTIVE, REPAIRED)])
                    if t.kind == "RELATIONAL"][0]
        site = code("if hasattr(self.file, 'seekable'):\n    return self.file.seekable()")
        patch = basis.candidates_from_node_templates(site, [template])[0]

        class Witness:
            def __init__(self, mode):
                self.mode = mode

            def __getattr__(self, name):
                if self.mode == "absent":
                    raise AttributeError(name)
                return None if self.mode == "none_valued" else object()

        def truth(expression, mode):
            tree = ast.parse(expression, mode="eval")
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and node.args:
                    node.args[0] = ast.Name(id="__w__", ctx=ast.Load())
            try:
                return bool(eval(compile(ast.fix_missing_locations(tree), "<probe>", "eval"),
                                 {"hasattr": hasattr, "getattr": getattr},
                                 {"__w__": Witness(mode)}))
            except AttributeError:
                return "AttributeError"

        old_calls = [ast.unparse(n) for n in ast.walk(ast.parse(site)) if isinstance(n, ast.Call)]
        new_calls = [ast.unparse(n) for n in ast.walk(ast.parse(patch["source"]))
                     if isinstance(n, ast.Call)]
        changed = [c for c in new_calls if c not in old_calls]
        self.assertEqual(len(changed), 1)
        new_expression = changed[0]
        self.assertTrue(new_expression.startswith("getattr("))

        for mode in ("ordinary", "absent"):
            self.assertEqual(truth("hasattr(x, 'seekable')", mode),
                             truth(new_expression, mode), mode)
        self.assertTrue(truth("hasattr(x, 'seekable')", "none_valued"))
        self.assertFalse(truth(new_expression, "none_valued"))


class TwoDemonstrationsDecideTheThirdSite(unittest.TestCase):
    """Where a fix IS expressible, two sites must determine a third without being told which."""

    HANDLERS = (
        "_validate_iat", "_validate_nbf", "_validate_exp")
    BODY = """
def {name}(self, payload, now, leeway):
    try:
        value = int(payload['{claim}'])
    except {excepts}:
        raise DecodeError('claim must be an integer') from None
    return value
"""
    CLAIMS = {"_validate_iat": "iat", "_validate_nbf": "nbf", "_validate_exp": "exp"}

    def program(self, excepts):
        return code("\n".join(self.BODY.format(name=name, claim=self.CLAIMS[name], excepts=excepts)
                              for name in self.HANDLERS))

    def test_third_site_is_recovered_exactly(self):
        defective, repaired = self.program("ValueError"), self.program("(ValueError, TypeError)")
        pairs = [(name, defective, repaired) for name in self.HANDLERS[:2]]
        templates = basis.induce_node_templates(pairs, context_depth=2)
        self.assertTrue(templates)

        third_defective = code(self.BODY.format(name="_validate_exp", claim="exp",
                                                excepts="ValueError"))
        third_repaired = code(self.BODY.format(name="_validate_exp", claim="exp",
                                               excepts="(ValueError, TypeError)"))
        patches = basis.candidates_from_node_templates(third_defective, templates)
        self.assertEqual(len(patches), 1)
        self.assertEqual(ast.dump(ast.parse(patches[0]["source"])),
                         ast.dump(ast.parse(third_repaired)))


if __name__ == "__main__":
    unittest.main()
