"""A slot reads the value the sentence states for it -- and nothing else.

Three measured defects, all in `composer_route_v1.bind`, all found on the repair
family that the public runner scores 0/50 on five separate capabilities:

1. ARGV ran to the end of the sentence.  "… using test command "python3 T" and save
   output_path O." bound test_argv = ["python3 T", "and", "save", "output_path", "O"].
   The quotes are the sentence saying where the command ends.

2. PATH_LIST produced one string, chosen by the single-path rules, so a list slot
   got whichever path ranked first: test_paths bound the SOURCE file while the
   sentence stated three test files.

3. PATH_DIR could not be filled from the sentence at all -- `extract_paths` returns
   files -- so it fell through and took a file: source_root bound <dir>/test_x.py,
   and the step raised SOURCE_ROOT_INVALID about a sentence that named the tree.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import composer_route_v1 as croute  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/binding_unit_tests"
REL = str(WORK.relative_to(ROOT))


def _make_tree() -> dict:
    """A real tree on disk: the bindings below only ever name files that exist."""
    tree = WORK / "tree"
    (tree).mkdir(parents=True, exist_ok=True)
    (tree / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    for name in ("test_a.py", "test_b.py", "test_c.py"):
        (tree / name).write_text("import unittest\n", encoding="utf-8")
    return {"tree": f"{REL}/tree", "source": f"{REL}/tree/calc.py",
            "tests": [f"{REL}/tree/test_a.py", f"{REL}/tree/test_b.py", f"{REL}/tree/test_c.py"],
            "report": f"{REL}/report.json"}


class AQuotedCommandEndsAtItsClosingQuote(unittest.TestCase):
    def test_the_tail_of_the_sentence_is_not_part_of_the_command(self):
        t = _make_tree()
        goal = (f'Repair python bug in source {t["source"]} with ast patch search guided by '
                f'test {t["tests"][0]} using test command "python3 {t["tests"][0]}" and save '
                f'output_path {t["report"]}.')
        argv = croute.extract_argv(goal)
        self.assertEqual(["python3", t["tests"][0]], argv)

    def test_a_quoted_command_with_a_trailing_comma_in_the_quote_is_not_split_badly(self):
        t = _make_tree()
        goal = (f'Run the strict progress repair loop on the python source root {t["tree"]} '
                f'with the test {t["tests"][0]} and test command '
                f'"/usr/bin/python3 {t["tests"][0]}", and save the repair report to {t["report"]}.')
        self.assertEqual(["/usr/bin/python3", t["tests"][0]], croute.extract_argv(goal))

    def test_an_unquoted_stated_command_still_reads_to_the_end(self):
        """Control: the fallthrough that has always worked keeps working."""
        argv = croute.extract_argv("Run the shell command mkdir /tmp/plain_dir")
        self.assertIsNotNone(argv)
        self.assertEqual("mkdir", argv[0])


class AListSlotTakesTheListTheSentenceStates(unittest.TestCase):
    def test_the_test_corpus_is_the_tests_not_the_source(self):
        t = _make_tree()
        goal = (f'Repair the python source {t["source"]} with the test guided repair loop so '
                f'that the unit tests in {t["tests"][0]}, {t["tests"][1]}, {t["tests"][2]} pass, '
                f'and save the repair report to {t["report"]}.')
        args = croute.bind({"test_paths": "PATH_LIST", "output_path": "PATH_OUTPUT"}, goal)
        self.assertEqual(t["tests"], args["test_paths"])
        self.assertEqual(t["report"], args["output_path"])

    def test_a_list_slot_always_answers_with_a_list(self):
        """`source_paths` was a string while `test_paths` was a list, in one call."""
        t = _make_tree()
        goal = (f'Repair the python source {t["source"]} with the test guided repair loop so '
                f'that the unit tests in {t["tests"][0]} pass, and save the report to {t["report"]}.')
        args = croute.bind({"source_paths": "PATH_LIST", "test_paths": "PATH_LIST"}, goal)
        self.assertIsInstance(args["source_paths"], list)
        self.assertEqual([t["source"]], args["source_paths"])
        self.assertEqual([t["tests"][0]], args["test_paths"])

    def test_a_destination_is_not_part_of_the_list(self):
        t = _make_tree()
        goal = (f'Repair the python source {t["source"]} so that the tests in {t["tests"][0]}, '
                f'{t["tests"][1]} pass, and save the report to {t["report"]}.')
        args = croute.bind({"test_paths": "PATH_LIST"}, goal)
        self.assertNotIn(t["report"], args["test_paths"])


class ADirectorySlotTakesADirectory(unittest.TestCase):
    def test_the_stated_tree_is_bound_as_a_tree(self):
        t = _make_tree()
        goal = (f'Run the strict progress repair loop on the python source root {t["tree"]} with '
                f'the test {t["tests"][0]} and save the report to {t["report"]}.')
        args = croute.bind({"source_root": "PATH_DIR"}, goal)
        self.assertEqual(t["tree"], args["source_root"])
        self.assertTrue((ROOT / args["source_root"]).is_dir())

    def test_it_never_invents_a_directory_that_is_not_there(self):
        t = _make_tree()
        goal = (f'Run the strict progress repair loop on the python source root {REL}/absent_dir '
                f'with the test {t["tests"][0]} and save the report to {t["report"]}.')
        args = croute.bind({"source_root": "PATH_DIR"}, goal)
        self.assertNotEqual(f"{REL}/absent_dir", args.get("source_root"))


class TheSentenceIsStillTheSource(unittest.TestCase):
    """The controls from the earlier slot work must keep binding exactly as before."""

    def test_input_first_output_last_for_a_compression(self):
        t = _make_tree()
        goal = f"Compress {t['source']} into {REL}/tree/notes.txt.gz"
        args = croute.bind({"input_path": "PATH_INPUT", "output_path": "PATH_OUTPUT"}, goal)
        self.assertEqual(t["source"], args["input_path"])
        self.assertEqual(f"{REL}/tree/notes.txt.gz", args["output_path"])

    def test_no_paths_binds_nothing(self):
        args = croute.bind({"source_path": "PATH_FILE"}, "Repair the python source.")
        self.assertEqual({}, args)


if __name__ == "__main__":
    unittest.main(verbosity=2)
