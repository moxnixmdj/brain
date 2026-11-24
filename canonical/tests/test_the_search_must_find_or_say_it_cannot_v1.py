"""The search must find what is findable, and must say so when it cannot.

§A154 measured two live outcomes through this module and left it without fixtures. That is the
gap this file closes, and it exists because a search that is only ever run against two known-good
instances has demonstrated nothing about the other 26 points in its space.

Two properties matter, and they pull in opposite directions:

    SOUNDNESS   a candidate is reported only after the benchmark's own tests accept it
    HONESTY     when nothing in the space works, the report says NONE_OF_THE_SPACE -- a
                statement about this search, not a claim about the task

The second is the one a hurried build skips. A search that reports "found" without confirming, or
that quietly widens itself until something passes, would have produced the §A154 NEW SYMBOL result
while being useless on everything else. Both are pinned below.

The seven defects from §A154 are also pinned, because each of them made the harness agree with
itself, and each is a one-line regression away from coming back.
"""

from __future__ import annotations

import ast
import pathlib
import shutil
import sys
import tempfile
import textwrap
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import search_a_body_under_the_test_v1 as S  # noqa: E402


class TheSpaceIsSound(unittest.TestCase):
    """Every point in the space must be installable python, not merely intended to be."""

    def test_every_candidate_compiles_as_a_class_member(self) -> None:
        """Defect 2/3: 4-space indent and stripped nesting both produced IndentationError.

        Compiled WHERE IT WILL BE INSTALLED -- inside a class, at 8 spaces -- because compiling
        it at module level passes for the wrong reason and hides the defect.
        """
        broken = []
        for name, body in S.candidates():
            src = ("def _as_text(v):\n    return str(v)\n\n\nclass N:\n"
                   "    def m(self, arg):\n" + body + "\n")
            try:
                compile(src, "<candidate>", "exec")
            except SyntaxError as exc:
                broken.append((name, str(exc)[:60]))
        self.assertEqual(broken, [], "every point in the space must be installable python")

    def test_a_hole_is_a_token_and_not_a_substring(self) -> None:
        """Defect 1: `"{T}" in template` hijacked every shape containing a dict literal."""
        # filter_token_classify_two contains '{' in its body and no type hole at all.
        names = [n for n, _ in S.candidates()]
        self.assertGreater(len(names), 0)
        body = dict(S.candidates(literals={"K0": "ipv4", "K1": "ipv6", "TOK": "local"}))[
            "filter_token_classify_two"]
        self.assertIn("'ipv4'", body)
        self.assertNotIn("dict", body.replace("dictionary", ""),
                         "a shape with no hole must not receive a type substitution")

    def test_parameter_names_are_substituted_on_word_boundaries_only(self) -> None:
        """Defect 4: `str.replace('arg', name)` turned `_argv` into `_ip_pathv`."""
        body = dict(S.candidates(literals={"ARGV": "[[1]]", "CALLER": "f(_argv)"},
                                 arg_name="ip_path"))["call_each_variant_then_parse"]
        self.assertIn("_argv", body, "an identifier merely CONTAINING 'arg' must survive")
        self.assertNotIn("_ip_pathv", body)


class TheConstantsComeFromTheSpecification(unittest.TestCase):
    """Literals are read from the test, never supplied by the caller and never from gold."""

    SPEC = textwrap.dedent('''
        IP4 = """
        broadcast 127.0.0.0 dev lo
        local 127.0.0.1 dev lo
        """

        IP6 = """
        local ::1 dev lo
        multicast ff00::/8 dev x
        """

        EXPECTED = {'ipv4': ['127.0.0.1'], 'ipv6': ['::1']}

        def run_command(self, command):
            if command == ['ip', '-4', 'route']:
                return 0, IP4, ''
            if command == ['ip', '-6', 'route']:
                return 0, IP6, ''
            return 1, '', ''
    ''')

    def test_bucket_names_are_the_expected_mappings_own_keys(self) -> None:
        lits = S.literals_from_spec(self.SPEC)
        self.assertEqual((lits["K0"], lits["K1"]), ("ipv4", "ipv6"))

    def test_the_filter_token_is_derived_by_replaying_the_spec(self) -> None:
        """The token whose lines REPRODUCE the expected mapping wins.

        Alphabetical or positional choice picked 'broadcast' on the real instance -- a token that
        produces an empty answer for every bucket. Replay is the only derivation that works.
        """
        lits = S.literals_from_spec(self.SPEC)
        self.assertEqual(lits["TOK"], "local")

    def test_the_call_arguments_are_the_tests_own_argv_lists(self) -> None:
        lits = S.literals_from_spec(self.SPEC)
        self.assertIn("['ip', '-4', 'route']", lits["ARGV"])
        self.assertIn("['ip', '-6', 'route']", lits["ARGV"])

    def test_a_spec_with_no_expected_mapping_yields_no_invented_keys(self) -> None:
        lits = S.literals_from_spec("def test_x():\n    assert f(1) == 2\n")
        self.assertEqual(lits["K0"], "")
        self.assertEqual(lits["K1"], "")


class TheVerdictIsTheBenchmarksNotTheSearchs(unittest.TestCase):
    """A candidate counts only when the named tests accept it. No partial credit exists."""

    def setUp(self) -> None:
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="search_", dir=REPO / "canonical" / "astra_runtime" / "tmp"))
        (self.root / "lib").mkdir()
        self.mod = self.root / "lib" / "mod.py"
        self.mod.write_text("class C:\n    pass\n", encoding="utf-8")
        self.test = self.root / "test_x.py"
        self.test.write_text(textwrap.dedent('''
            from lib.mod import C


            def test_wants_length():
                assert C().length([1, 2, 3]) == 3
        ''').replace("from lib.mod import C", "import sys\nsys.path.insert(0, 'lib')\nfrom mod import C"),
            encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_findable_body_is_found_and_confirmed(self) -> None:
        rep = S.search_body(self.root, owner_path=self.mod, owner_class="C", member="length",
                            params=["arg"], test_ids=["test_x.py::test_wants_length"],
                            test_source=self.test.read_text())
        self.assertTrue(rep["found"], rep)
        self.assertEqual(rep["outcome"], "FOUND_AND_CONFIRMED")
        self.assertIn("len(arg)", rep["body"])

    def test_an_unsatisfiable_requirement_reports_none_of_the_space(self) -> None:
        """The honest failure: a report about this search, not a claim about the task."""
        self.test.write_text(textwrap.dedent('''
            import sys
            sys.path.insert(0, 'lib')
            from mod import C


            def test_wants_the_impossible():
                assert C().length([1]) == "a value no primitive produces"
        '''), encoding="utf-8")
        rep = S.search_body(self.root, owner_path=self.mod, owner_class="C", member="length",
                            params=["arg"], test_ids=["test_x.py::test_wants_the_impossible"],
                            test_source=self.test.read_text())
        self.assertFalse(rep["found"])
        self.assertEqual(rep["outcome"], "NONE_OF_THE_SPACE")
        self.assertIn("space_size", rep)

    def test_the_module_is_restored_when_nothing_is_found(self) -> None:
        """A search that leaves its last failed candidate installed has edited the repository."""
        before = self.mod.read_text(encoding="utf-8")
        self.test.write_text(textwrap.dedent('''
            import sys
            sys.path.insert(0, 'lib')
            from mod import C


            def test_wants_the_impossible():
                assert C().length([1]) == "nope"
        '''), encoding="utf-8")
        S.search_body(self.root, owner_path=self.mod, owner_class="C", member="length",
                      params=["arg"], test_ids=["test_x.py::test_wants_the_impossible"],
                      test_source=self.test.read_text())
        self.assertEqual(self.mod.read_text(encoding="utf-8"), before,
                         "a failed search must leave the module exactly as it found it")

    def test_the_helper_is_emitted_only_when_a_chosen_body_uses_it(self) -> None:
        """A helper nobody calls is a part that does not justify itself."""
        S.search_body(self.root, owner_path=self.mod, owner_class="C", member="length",
                      params=["arg"], test_ids=["test_x.py::test_wants_length"],
                      test_source=self.test.read_text())
        self.assertIn("len(arg)", self.mod.read_text(encoding="utf-8"))
        self.assertNotIn("def _as_text", self.mod.read_text(encoding="utf-8"),
                         "this body never calls _as_text, so the helper must not be added")


if __name__ == "__main__":
    unittest.main()
