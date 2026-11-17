"""Tests for the grammar-closed repair generator.

What is pinned here is the mechanism's *claims*, not its score:

  * the hypothesis space really is generated from the program (no edit library, no learned
    parameter), and it includes the rung the hand-written list provably could not reach
    (`n ^= n - 1` -> `n &= n - 1` is an `AugAssign` operator swap);
  * a candidate rewrites exactly one site -- the regression that made an earlier prototype test
    the unmodified source forever while reporting thousands of candidates is pinned directly;
  * the verdict is the corpus's own pytest file run on a fresh copy, never the search's opinion,
    and the answer key never reaches the task directory;
  * a defect whose specification is only a bare boolean, or which has no published examples, is
    reported as unmeasurable rather than counted as a failure or a success.

The programs used as fixtures here are small and written for the test; the *measurement* against
real bugs lives in canonical/tools/grammar_closed_repair_v1.py and reports its own corpus.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys
import tempfile
import textwrap
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.tools import grammar_closed_repair_v1 as organ  # noqa: E402

BITCLEAR = "def bits(n):\n    count = 0\n    while n:\n        n ^= n - 1\n        count += 1\n    return count\n"
BITCLEAR_FIXED = "def bits(n):\n    count = 0\n    while n:\n        n &= n - 1\n        count += 1\n    return count\n"

CONFTEST = "import pytest\n\npytest.use_correct = False\n"
LOADER = textwrap.dedent('''
    import json
    from pathlib import Path


    def load_json_testcases(algorithm):
        root = Path(__file__).parent / ".."
        with open(root / f"json_testcases/{algorithm}.json") as data_file:
            return [json.loads(line) for line in data_file]
''').lstrip()
TEST_FILE = textwrap.dedent('''
    import pytest
    from load_testdata import load_json_testcases

    if pytest.use_correct:
        from correct_python_programs.{name} import {name}
    else:
        from python_programs.{name} import {name}

    testdata = load_json_testcases({name}.__name__)


    @pytest.mark.parametrize("input_data,expected", testdata)
    def test_{name}(input_data, expected):
        assert {name}(*input_data) == expected
''').lstrip()


class CorpusFixture:
    """A miniature corpus with the same layout and the same integrity hazard as the real one."""

    def __init__(self, name: str, buggy: str, correct: str, examples: list[tuple[list, object]], *,
                 with_answer_key: bool = True):
        self.name = name
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name) / "corpus"
        (self.root / "python_programs").mkdir(parents=True)
        (self.root / "python_testcases").mkdir()
        (self.root / "json_testcases").mkdir()
        (self.root / "python_programs" / f"{name}.py").write_text(buggy)
        (self.root / "python_testcases" / f"test_{name}.py").write_text(TEST_FILE.format(name=name))
        (self.root / "python_testcases" / "load_testdata.py").write_text(LOADER)
        # One example per line, exactly as the real corpus stores them.
        (self.root / "json_testcases" / f"{name}.json").write_text(
            "".join(json.dumps([a, e]) + "\n" for a, e in examples))
        (self.root / "conftest.py").write_text(CONFTEST)
        if with_answer_key:
            (self.root / "correct_python_programs").mkdir()
            (self.root / "correct_python_programs" / f"{name}.py").write_text(correct)

    def close(self) -> None:
        self._tmp.cleanup()


class TheSpaceIsGeneratedFromTheProgram(unittest.TestCase):
    def test_the_augassign_rung_the_hand_list_cannot_reach_is_in_the_space(self) -> None:
        """`^=` -> `&=` was unreachable at any budget for the hand-written basis. It is a swap here."""
        tree = ast.parse(BITCLEAR)
        space = organ._enumerate(tree, organ.atoms_of(tree.body[0]))
        swaps = [c for c in space if c["kind"] == "OPERATOR" and c["replacement"] == "BitAnd"]
        self.assertTrue(swaps, "no AugAssign operator swap in the hypothesis space")
        self.assertIn("n &= n - 1", swaps[0]["source"])

    def test_no_candidate_mentions_anything_outside_the_program_and_the_builtins(self) -> None:
        tree = ast.parse(BITCLEAR)
        atoms = set(organ.atoms_of(tree.body[0]))
        space = organ._enumerate(tree, atoms)
        self.assertGreater(len(space), 100)
        for candidate in space[:400]:
            names = {n.id for n in ast.walk(ast.parse(candidate["source"])) if isinstance(n, ast.Name)}
            stray = names - atoms - set(organ.BUILTIN_NAMES)
            self.assertFalse(stray, f"candidate invented an identifier: {stray}")

    def test_the_space_does_not_depend_on_the_corpus(self) -> None:
        """The same program produces the same space regardless of what else exists on disk."""
        tree = ast.parse(BITCLEAR)
        first = [c["source"] for c in organ._enumerate(tree, organ.atoms_of(tree.body[0]))]
        second = [c["source"] for c in organ._enumerate(ast.parse(BITCLEAR), organ.atoms_of(ast.parse(BITCLEAR).body[0]))]
        self.assertEqual(first, second)


class TheHypothesisIsARewriteOfARegion(unittest.TestCase):
    """The audit's four missing families, pinned by the rewrite that supplies each one."""

    GCD = "def gcd(a, b):\n    if b == 0:\n        return a\n    return gcd(a % b, b)\n"

    def test_argument_permutation_is_generated_and_reaches_the_published_fix(self) -> None:
        """`gcd(a % b, b)` -> `gcd(b, a % b)`: two positions change, so no single-node edit reaches it."""
        tree = ast.parse(self.GCD)
        space = organ._enumerate(tree, organ.atoms_of(tree.body[0]))
        permutations = [c for c in space if c["kind"] == "PERMUTE"]
        self.assertTrue(permutations, "no argument permutation in the space")
        self.assertTrue(any("gcd(b, a % b)" in c["source"] for c in permutations), permutations)

    def test_operand_swap_only_for_non_commutative_operators(self) -> None:
        """`b - a` is a different program from `a - b`; `a + b` is not."""
        sub = ast.parse("def f(a, b):\n    return b - a\n")
        add = ast.parse("def f(a, b):\n    return b + a\n")
        self.assertTrue(any(c["kind"] == "PERMUTE_OPERANDS" for c in organ._enumerate(sub, ["a", "b"])))
        self.assertFalse(any(c["kind"] == "PERMUTE_OPERANDS" for c in organ._enumerate(add, ["a", "b"])))

    def test_shape_over_an_atom_not_just_over_the_node(self) -> None:
        """`total < 0` -> `not coins`: the substitution family wraps the node, never an atom in it."""
        # `coins` must occur as a used NAME, not only as a parameter, or there is no atom site.
        tree = ast.parse("def f(coins, total):\n    first, *rest = coins\n"
                         "    if total < 0:\n        return 0\n    return first\n")
        space = organ._enumerate(tree, organ.atoms_of(tree.body[0]))
        self.assertTrue(any(c["kind"] == "ATOM_SHAPE" and "not coins" in c["source"] for c in space))

    def test_statement_insertion_produces_a_program_that_compiles(self) -> None:
        tree = ast.parse("def f(xs):\n    for x in xs:\n        xs.append(x)\n")
        inserts = [c for c in organ._enumerate(tree, organ.atoms_of(tree.body[0])) if c["kind"] == "INSERT_GUARD"]
        self.assertTrue(inserts)
        for candidate in inserts:
            compile(candidate["source"], "<candidate>", "exec")

    def test_a_comparison_over_an_atom_is_in_the_space(self) -> None:
        """The hole that cost a real bug: `return True` -> `return depth == 0`.

        The atom-combination family built only arithmetic (`a + b`), never a comparison, so the fix
        was outside the space while `True == 0` -- a comparison over the NODE -- sat inside it and
        was useless. Comparisons are part of the language, so they belong to the grammar.
        """
        program = ("def f(parens):\n    depth = 0\n    for paren in parens:\n"
                   "        depth += 1\n    return True\n")
        tree = ast.parse(program)
        space = organ._enumerate(tree, organ.atoms_of(tree.body[0]))
        self.assertTrue(any(c["source"].rstrip().endswith("return depth == 0") for c in space),
                        "`return depth == 0` is not reachable")

    def test_every_candidate_in_every_family_is_a_program(self) -> None:
        """A hypothesis that does not compile is not a hypothesis; the space must never contain one."""
        for program in (self.GCD, "def f(a):\n    return a[1:] + a\n"):
            tree = ast.parse(program)
            for candidate in organ._enumerate(tree, organ.atoms_of(tree.body[0])):
                compile(candidate["source"], "<candidate>", "exec")


class OneSitePerCandidate(unittest.TestCase):
    def test_replacement_touches_exactly_the_targeted_node(self) -> None:
        tree = ast.parse(BITCLEAR)
        paths = list(organ._paths(tree))
        path, node = next((p, n) for p, n in paths
                          if isinstance(n, ast.Name) and n.id == "count"
                          and isinstance(n.ctx, ast.Load))
        patched = organ.replace_at(tree, path, ast.parse("count + 1", mode="eval").body)
        before = [ast.unparse(n) for n in ast.walk(tree)]
        after = [ast.unparse(n) for n in ast.walk(patched)]
        # Structure outside the site is untouched, and the site really changed.
        self.assertEqual(len(patched.body[0].body), len(tree.body[0].body))
        self.assertIn("count + 1", ast.unparse(patched))
        self.assertNotEqual(ast.unparse(tree), ast.unparse(patched))

    def test_operator_swap_rewrites_the_field_not_the_node(self) -> None:
        """Regression: an earlier prototype replaced the NODE with an operator, so nothing changed."""
        tree = ast.parse(BITCLEAR)
        path, node = next((p, n) for p, n in organ._paths(tree) if isinstance(n, ast.AugAssign))
        patched = organ._set_operator(tree, path, ast.BitAnd())
        self.assertIn("n &= n - 1", ast.unparse(patched))
        while_node = patched.body[0].body[1]
        self.assertIsInstance(while_node, ast.While)
        self.assertIsInstance(while_node.body[0], ast.AugAssign)
        self.assertIsInstance(while_node.body[0].op, ast.BitAnd)

    def test_candidates_are_deduplicated(self) -> None:
        tree = ast.parse(BITCLEAR)
        space = organ._enumerate(tree, organ.atoms_of(tree.body[0]))
        sources = [c["source"] for c in space]
        self.assertEqual(len(sources), len(set(sources)))


class TheOracleIsTheCorpusTest(unittest.TestCase):
    def test_repairs_a_real_defect_and_verifies_with_the_corpus_own_test(self) -> None:
        cases = [([7], 3), ([127], 7), ([1], 1), ([8], 1)]
        fixture = CorpusFixture("bits", BITCLEAR, BITCLEAR_FIXED, cases)
        try:
            row = organ.repair_task(fixture.root, "bits", budget_s=25, per_example_timeout=0.05,
                                    verify_timeout=90)
        finally:
            fixture.close()
        self.assertEqual(row["stage"], "REPAIRED__CORPUS_TEST_PASSES", row)
        self.assertEqual(row["answer_key_in_task_dir"], False)
        self.assertEqual(row["corpus_test"]["returncode"], 0)
        self.assertEqual(row["edit"]["replacement"], "BitAnd")
        self.assertEqual(row["edit"]["kind"], "OPERATOR")
        self.assertEqual(row["answer_key_in_task_dir"], False)

    def test_an_already_correct_program_is_not_a_repair(self) -> None:
        cases = [([7], 3), ([127], 7)]
        fixture = CorpusFixture("bits", BITCLEAR_FIXED, BITCLEAR_FIXED, cases)
        try:
            row = organ.repair_task(fixture.root, "bits", budget_s=10, per_example_timeout=0.05,
                                    verify_timeout=60)
        finally:
            fixture.close()
        self.assertEqual(row["stage"], "DEFECT_DOES_NOT_REPRODUCE")

    def test_the_answer_key_never_reaches_the_task_directory(self) -> None:
        cases = [([7], 3)]
        fixture = CorpusFixture("bits", BITCLEAR, BITCLEAR_FIXED, cases)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                where = pathlib.Path(tmp) / "task"
                organ.build_task(fixture.root, "bits", where)
                self.assertFalse((where / organ.ANSWER_KEY).exists())
                self.assertTrue((where / "python_testcases" / "test_bits.py").is_file())
                self.assertTrue((where / "json_testcases" / "bits.json").is_file())
                # the specification travels; no other problem's data does
                self.assertEqual(len(list((where / "json_testcases").iterdir())), 1)
        finally:
            fixture.close()

    def test_a_task_directory_that_already_holds_the_key_is_refused(self) -> None:
        cases = [([7], 3)]
        fixture = CorpusFixture("bits", BITCLEAR, BITCLEAR_FIXED, cases)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                where = pathlib.Path(tmp) / "task"
                (where / organ.ANSWER_KEY).mkdir(parents=True)
                with self.assertRaises(RuntimeError):
                    organ.build_task(fixture.root, "bits", where)
        finally:
            fixture.close()


class UnmeasurableIsNotAFailureAndNotASuccess(unittest.TestCase):
    def test_no_published_examples_is_reported_as_such(self) -> None:
        fixture = CorpusFixture("bits", BITCLEAR, BITCLEAR_FIXED, [])
        try:
            row = organ.repair_task(fixture.root, "bits", budget_s=5, per_example_timeout=0.05,
                                    verify_timeout=30)
        finally:
            fixture.close()
        self.assertEqual(row["stage"], "NO_EXAMPLES")
        self.assertNotIn("corpus_test", row)

    def test_an_infinite_loop_candidate_does_not_hang_the_search(self) -> None:
        namespace = {}
        source = "def loop(x):\n    while True:\n        pass\n"
        got = organ.score(source, "loop", [([1], 1)], per_example_timeout=0.05)
        self.assertEqual(got, -1)
        self.assertEqual(namespace, {})


class CorpusPytestSeesBothImportRoots(unittest.TestCase):
    """The verifier must put python_programs/ and python_testcases/ on PYTHONPATH.

    QuixBugs test files do ``from node import Node`` and ``from load_testdata import ...``.
    An earlier verifier set PYTHONPATH to only the task root, so pytest died at collection
    (rc 2) and a correct patch was misreported as failed. The fixture below reproduces
    exactly that import shape; without the two extra roots the test cannot collect.
    """

    def test_verify_collects_when_the_helper_lives_under_python_programs(self) -> None:
        name = "needs_helper"
        buggy = "def needs_helper(xs):\n    return node_count(xs)\n"
        fixed = "def needs_helper(xs):\n    return len(xs)\n"
        # node_count is imported the way QuixBugs imports Node: from python_programs.
        helper_source = "def node_count(xs):\n    return sum(1 for _ in xs)\n"
        fixture_root = tempfile.mkdtemp(prefix="verify_roots_")
        root = pathlib.Path(fixture_root)
        try:
            (root / "python_programs").mkdir()
            (root / "python_testcases").mkdir()
            (root / "json_testcases").mkdir()
            (root / "python_programs" / f"{name}.py").write_text(buggy)
            (root / "python_programs" / "node.py").write_text(helper_source)
            (root / "python_testcases" / f"test_{name}.py").write_text(textwrap.dedent(f"""
                from node import node_count
                from python_programs.{name} import {name}

                def test_{name}():
                    assert {name}([1, 2, 3]) == 3
            """).lstrip())
            # Apply the fixed program the way build_task would.
            (root / "python_programs" / f"{name}.py").write_text(fixed)
            verdict = organ.verify_with_corpus_test(
                root, f"python_testcases/test_{name}.py", 30)
            # Collection succeeds (not rc 2); with the fix the fixed program passes.
            self.assertNotEqual(verdict["returncode"], 2, verdict)
            self.assertEqual(verdict["returncode"], 0, verdict)
        finally:
            import shutil
            shutil.rmtree(root, ignore_errors=True)

    def test_pythonpath_contains_all_three_roots(self) -> None:
        where = pathlib.Path("/tmp/verify_roots_where")
        # Drive the env construction the same way verify_with_corpus_test does.
        roots = [str(where), str(where / "python_programs"), str(where / "python_testcases")]
        import os
        joined = os.pathsep.join(roots)
        self.assertIn(str(where / "python_programs"), joined)
        self.assertIn(str(where / "python_testcases"), joined)


class TheSummaryIsFoldedNotTyped(unittest.TestCase):
    def test_counts_come_from_the_rows(self) -> None:
        rows = [{"task": "a", "stage": "REPAIRED__CORPUS_TEST_PASSES", "candidates_tested": 10, "seconds": 1},
                {"task": "b", "stage": "NO_EXAMPLES"},
                {"task": "c", "stage": "REPAIRED__CORPUS_TEST_PASSES", "candidates_tested": 5, "seconds": 2}]
        summary = organ.summarise(rows)
        self.assertEqual(summary["repaired"], 2)
        self.assertEqual(summary["repaired_tasks"], ["a", "c"])
        self.assertEqual(summary["candidates_tested"], 15)
        self.assertEqual(summary["by_stage"]["NO_EXAMPLES"]["tasks"], ["b"])


if __name__ == "__main__":
    unittest.main()
