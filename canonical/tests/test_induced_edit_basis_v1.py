"""Tests of the induced edit basis: where an edit comes from, and where it is allowed to act.

These tests are about the MECHANISM, so the programs in them are small and written here on purpose --
the corpus itself is the subject of `test_quixbugs_*.py` and of the receipt, not of a unit test.

What is pinned, in the order the claims matter:
  * a demonstration is folded into a template, and a template names its demonstrations;
  * an edit that changes the SHAPE of the code is refused, not approximated;
  * operator leaves are visible at all (the `^=` -> `&=` case, unreachable by the hand-listed basis);
  * a node-level demonstration generalizes to a hole pattern rather than to a literal string, and
    that pattern fires in a different program;
  * a template fires only where its precondition literally holds;
  * two sibling statements cannot be confused, because a site is identified by its path;
  * the rung a fix sits on is computed from the fix.
"""
from __future__ import annotations

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


class InductionOfLeafEdits(unittest.TestCase):
    def test_operator_pair_on_an_augmented_assignment_is_induced(self):
        """`n ^= n - 1` -> `n &= n - 1` is invisible to a basis with no AugAssign rule."""
        defective = code("def bitcount(n):\n    count = 0\n    while n:\n        n ^= n - 1\n        count += 1\n    return count")
        repaired = defective.replace("^=", "&=")
        templates = basis.induce_templates([("bitcount", defective, repaired)])
        pairs = [t for t in templates if t.executable]
        self.assertTrue(pairs, "an augmented-assignment operator change must be expressible")
        self.assertEqual(pairs[0].kind, "OP_PAIR")
        self.assertEqual(pairs[0].node_type, "AugAssign")
        self.assertEqual((pairs[0].old, pairs[0].new), ("BitXor", "BitAnd"))

    def test_documentation_is_not_a_repair(self):
        """An inert string statement is not an edit; a docstring-only difference teaches nothing."""
        defective = code('def f(x):\n    """doc"""\n    return x')
        repaired = code('def f(x):\n    return x\n\n"""a trailing note"""')
        templates = basis.induce_templates([("f", defective, repaired)])
        self.assertEqual([t for t in templates if t.executable], [])
        self.assertEqual(basis.induce_node_templates([("f", defective, repaired)]), [])

    def test_statement_insertion_is_refused_with_a_reason(self):
        defective = code("def f(n):\n    for i in range(2, n):\n        if n % i == 0:\n            return [i]\n    return []")
        repaired = code("def f(n):\n    for i in range(2, n):\n        if n % i == 0:\n            return [i]\n    return [n]")
        refused = [t for t in basis.induce_templates([("f", defective, repaired)]) if not t.executable]
        self.assertTrue(refused, "changing a return value here is a literal substitution, not a shape change")
        # A genuinely inserted statement must be refused rather than approximated.
        inserted = code("def f(n):\n    if n == 0:\n        return 0\n    return 1")
        templates = basis.induce_templates([("g", code("def f(n):\n    return 1"), inserted)])
        self.assertTrue(all(not t.executable for t in templates))
        self.assertIn("STATEMENT_INSERT", {t.reason for t in templates})

    def test_support_counts_distinct_demonstrations(self):
        a = code("def f(x, top):\n    if x < top:\n        return x\n    return top")
        b = a.replace("<", "<=")
        templates = basis.induce_templates([("one", a, b), ("two", a, b)])
        executable = [t for t in templates if t.executable]
        self.assertEqual(len(executable), 1)
        self.assertEqual(executable[0].support, 2)
        self.assertEqual(executable[0].taught_by, ("one", "two"))

    def test_refused_templates_never_produce_candidates(self):
        defective = code("def f(n):\n    return 1")
        repaired = code("def f(n):\n    if n == 0:\n        return 0\n    return 1")
        templates = basis.induce_templates([("g", defective, repaired)])
        self.assertEqual(basis.candidates_from_templates(defective, templates), [])


class ApplyingTemplates(unittest.TestCase):
    def test_a_template_fires_in_a_different_program_and_only_at_its_precondition(self):
        """Taught on one program; the same operator appears in another and is changed there."""
        taught = basis.induce_templates([(
            "at_most",
            code("def at_most(x, top):\n    if x < top:\n        return x\n    return top"),
            code("def at_most(x, top):\n    if x <= top:\n        return x\n    return top"))])
        elsewhere = code("def clamp(x, hi):\n    if x < hi:\n        return x\n    return hi")
        candidates = basis.candidates_from_templates(elsewhere, taught)
        self.assertEqual(len(candidates), 1)
        self.assertIn("<=", candidates[0]["source"])
        self.assertEqual(candidates[0]["template"]["taught_by"], ["at_most"])

    def test_nothing_fires_where_the_old_value_is_absent(self):
        taught = basis.induce_templates([(
            "at_most",
            code("def at_most(x, top):\n    if x < top:\n        return x\n    return top"),
            code("def at_most(x, top):\n    if x <= top:\n        return x\n    return top"))])
        already_right = code("def clamp(x, hi):\n    if x <= hi:\n        return x\n    return hi")
        self.assertEqual(basis.candidates_from_templates(already_right, taught), [])

    def test_sibling_statements_are_not_confused(self):
        """Two `^=` statements in one function: the site is its path, not its type."""
        defective = code("def f(n):\n    n ^= 1\n    n ^= 2\n    return n")
        taught = basis.induce_templates([(
            "bitcount", code("def g(n):\n    n ^= n - 1\n    return n"),
            code("def g(n):\n    n &= n - 1\n    return n"))])
        candidates = basis.candidates_from_templates(defective, taught)
        sites = [tuple(tuple(step) for step in c["site_path"]) for c in candidates]
        self.assertEqual(len(candidates), 2)
        self.assertEqual(len(set(sites)), 2, "each site must be distinct")
        for candidate in candidates:
            self.assertEqual(candidate["source"].count("&="), 1, "exactly one statement may change")


class InductionOfNodeEdits(unittest.TestCase):
    def test_a_node_edit_generalizes_to_a_hole_not_a_literal(self):
        """`mid` -> `mid + 1` must be learned as `H -> H + 1`, or it teaches nothing but `mid`."""
        templates = basis.induce_node_templates([(
            "find_in_sorted",
            code("def f(arr, x):\n    mid = len(arr) // 2\n    return search(arr, mid, x)"),
            code("def f(arr, x):\n    mid = len(arr) // 2\n    return search(arr, mid + 1, x)"))])
        relational = [t for t in templates if t.kind == "RELATIONAL"]
        self.assertEqual(len(relational), 1)
        self.assertIn(basis.HOLE_PREFIX, relational[0].new_pattern)
        self.assertNotIn("mid", relational[0].new_pattern)

    def test_a_hole_pattern_fires_in_another_program(self):
        templates = basis.induce_node_templates([(
            "find_in_sorted",
            code("def f(arr, x):\n    mid = len(arr) // 2\n    return search(arr, mid, x)"),
            code("def f(arr, x):\n    mid = len(arr) // 2\n    return search(arr, mid + 1, x)"))])
        pascal = code("def pascal(n):\n    for r in range(n):\n        for c in range(0, r):\n            pass")
        candidates = basis.candidates_from_node_templates(pascal, templates)
        self.assertTrue(candidates, "a learned hole pattern must be able to fire in a new program")
        self.assertTrue(any("r + 1" in c["source"] for c in candidates))
        self.assertTrue(all(c["template"]["taught_by"] == ["find_in_sorted"] for c in candidates))

    def test_wrapping_is_expressed_as_containment(self):
        """`sum` becomes `max(0, sum)`: the old node is inside the new one, so the hole carries it."""
        templates = basis.induce_node_templates([(
            "max_sublist_sum",
            code("def f(arr):\n    best = 0\n    for x in arr:\n        best = best + x\n    return best"),
            code("def f(arr):\n    best = 0\n    for x in arr:\n        best = max(0, best + x)\n    return best"))])
        relational = [t for t in templates if t.kind == "RELATIONAL"]
        self.assertEqual(len(relational), 1)
        self.assertIn("max", relational[0].new_pattern)
        self.assertIn(basis.HOLE_PREFIX, relational[0].new_pattern)

    def test_repeated_holes_must_bind_equal_subtrees(self):
        bindings: dict[str, object] = {}
        pattern = basis._parse_pattern("__brain_hole_0__ + __brain_hole_0__", "EXPR")
        self.assertIsNotNone(pattern)
        self.assertFalse(basis._unify(pattern, basis._parse_pattern("a + b", "EXPR"), bindings))
        bindings = {}
        same = basis._parse_pattern("a + a", "EXPR")
        self.assertTrue(basis._unify(pattern, same, bindings))
        self.assertIn("__brain_hole_0__", bindings)

    def test_a_statement_node_edit_is_induced_in_statement_mode(self):
        """`continue` -> `break` has no expression underneath it, so the site IS the statement."""
        templates = basis.induce_node_templates([(
            "loop",
            code("def f(xs):\n    for x in xs:\n        if x:\n            continue\n    return xs"),
            code("def f(xs):\n    for x in xs:\n        if x:\n            break\n    return xs"))])
        self.assertTrue(templates)
        self.assertEqual({t.mode for t in templates}, {"STMT"})
        self.assertEqual({t.root_type for t in templates}, {"Continue"})

    def test_an_expression_under_a_changed_statement_is_preferred(self):
        """`.update(x)` -> `= x` differs at the statement AND below it; the deeper lesson wins."""
        templates = basis.induce_node_templates([(
            "mst",
            code("def f(g, node, u):\n    for node, u in g:\n        group[node].update(group[u])\n    return group"),
            code("def f(g, node, u):\n    for node, u in g:\n        group[node] = group[u]\n    return group"))])
        self.assertEqual({t.mode for t in templates}, {"EXPR"})


class TheLadder(unittest.TestCase):
    def test_rungs_are_computed_from_the_pairs(self):
        leaf = basis.classify_fix_shape(code("def f(x, t):\n    if x < t:\n        return x\n    return t"),
                                        code("def f(x, t):\n    if x <= t:\n        return x\n    return t"))
        self.assertEqual(leaf["rung"], "RUNG_LEAF")

        node = basis.classify_fix_shape(code("def f(a, m, x):\n    return s(a, m, x)"),
                                        code("def f(a, m, x):\n    return s(a, m + 1, x)"))
        self.assertEqual(node["rung"], "RUNG_NODE")

        multi = basis.classify_fix_shape(code("def f(a):\n    return [1] + a + [2]"),
                                         code("def f(a):\n    return [2] + a + [1]"))
        self.assertEqual(multi["rung"], "RUNG_MULTI")

        shape = basis.classify_fix_shape(code("def f(n):\n    return 1"),
                                         code("def f(n):\n    if n:\n        return 1\n    return 0"))
        self.assertEqual(shape["rung"], "RUNG_SHAPE")

    def test_a_docstring_only_difference_is_no_change_at_all(self):
        self.assertEqual(basis.classify_fix_shape(code('def f(x):\n    return x'),
                                                  code('def f(x):\n    """doc"""\n    return x'))["rung"],
                         "NO_CHANGE")


if __name__ == "__main__":
    unittest.main()
