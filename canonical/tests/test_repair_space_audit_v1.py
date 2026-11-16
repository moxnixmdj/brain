"""Tests for the audit that says whether a refusal was search or expressiveness.

The audit reads the corpus's corrected programs. That is legitimate for an audit of the target and
forbidden for the solver, so the property pinned here is that the two stay separate: the audit must
compare at the level of the TARGET FUNCTION (QuixBugs' corrected files sometimes ship several
implementations plus the task description as a string), and it must classify into the three
verdicts that call for three different next builds.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.tools import repair_space_audit_v1 as audit  # noqa: E402

GCD_BAD = "def gcd(a, b):\n    if b == 0:\n        return a\n    return gcd(a % b, b)\n"
GCD_GOOD = "def gcd(a, b):\n    if b == 0:\n        return a\n    return gcd(b, a % b)\n"
#: a corrected file that ALSO carries an extra implementation and the task description, exactly as
#: several QuixBugs files do -- a module-level comparison would misread this as "not in the space"
GCD_GOOD_WITH_EXTRA = GCD_GOOD + '\n\ndef gcd(a, b):\n    while b:\n        a, b = b, a % b\n    return a\n\n"""GCD."""\n'


class TheUnitOfComparisonIsTheFunction(unittest.TestCase):
    def test_a_second_implementation_in_the_corrected_file_does_not_hide_the_fix(self) -> None:
        self.assertEqual(audit.function_source(GCD_GOOD, "gcd"), ast.unparse(ast.parse(GCD_GOOD).body[0]))
        self.assertEqual(audit.function_source(GCD_GOOD_WITH_EXTRA, "gcd"),
                         audit.function_source(GCD_GOOD, "gcd"))

    def test_an_inert_trailing_string_is_not_part_of_the_answer(self) -> None:
        with_string = GCD_GOOD + '\n"""the task description"""\n'
        self.assertEqual(audit.function_source(with_string, "gcd"),
                         audit.function_source(GCD_GOOD, "gcd"))

    def test_a_missing_target_function_is_not_silently_a_different_function(self) -> None:
        self.assertIsNone(audit.function_source(GCD_GOOD, "not_here"))


class TheThreeVerdictsAreDistinguished(unittest.TestCase):
    def test_a_one_edit_fix_that_the_space_contains_is_a_search_failure(self) -> None:
        from canonical.tools import grammar_closed_repair_v1 as organ
        tree = ast.parse(GCD_BAD)
        space = organ._enumerate(tree, organ.atoms_of(tree.body[0]))
        answer = audit.function_source(GCD_GOOD, "gcd")
        inside = any(audit.function_source(c["source"], "gcd") == answer for c in space)
        self.assertTrue(inside, "the permutation rewrite should reach gcd's published fix")

    def test_two_disjoint_sites_are_multi_edit(self) -> None:
        from canonical.tools import quixbugs_required_edit_taxonomy_v1 as taxonomy
        bad = "def f(a, b):\n    x = a + b\n    return x - 1\n"
        good = "def f(a, b):\n    x = a * b\n    return x - 2\n"
        self.assertGreater(taxonomy.classify(bad, good)["edit_count"], 1)

    def test_the_multi_edit_count_is_a_LOWER_bound_and_this_pins_why(self) -> None:
        """A nested change is reported at the shallowest explaining site, so C_MULTI_EDIT is
        conservative: two changes hidden under one node count as one. The audit says so."""
        from canonical.tools import quixbugs_required_edit_taxonomy_v1 as taxonomy
        swallowed = taxonomy.classify("def f(a):\n    return a + 1\n",
                                     "def f(a):\n    return (a + 2) * 3\n")
        self.assertEqual(swallowed["edit_count"], 1)
        self.assertEqual(swallowed["kinds"], ["OPERATOR"])


if __name__ == "__main__":
    unittest.main()
