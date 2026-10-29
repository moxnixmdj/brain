"""A directory a sentence names absolutely must survive, and "which files hold
the text" must be answered by reading the files.

Three defects, each measured on ``90c8c84`` through ``solve()``
--------------------------------------------------------------

1. ``_DIRPATH`` could not start with a slash, because its character class is a run
   of ``segment/`` and excludes ``/`` itself.  ``_EXT`` has ``/`` inside its class,
   so an absolute FILE survived extraction intact while an absolute DIRECTORY came
   out missing its leading slash: ``/home/user/brain/canonical/x`` was read as
   ``home/user/brain/canonical/x`` -- a repository-relative path that points
   nowhere.  Every command then ran with cwd at the repository root and reported
   ``No such file or directory`` for a directory that exists, as
   ``STEP_RAISED_OUTCOME_UNKNOWN``.  Measured on both spellings of the same tree.

2. ``grep`` on a directory without ``-r`` is an error, not an answer -- the law is
   already written in the comment above the flag.  The code only ever read the
   sentence's own words, so "Search the directory D for 'gamma'" (no "files ... in
   the ... directory") ran ``grep gamma D`` and failed with ``Is a directory``.
   Whether the operand IS a directory is a fact about the disk, and
   ``_is_directory_in_repo`` already answers it for the slots that need that fact.

3. "Show which files in the directory D contain 'gamma'" bound ``ls D`` and was
   certified ``pass=True`` with a list of names.  That is the worst shape there
   is: a perfectly reproducible answer to a question nobody asked, since not one
   of those names says whether the file holds the text.  The row that caught it
   maps "files ... directory" to ``ls``, and by that table's own stated order rule
   the narrower claim about a path must come before the general one about a
   directory.  A sentence that states text to look for INSIDE the files is the
   narrower claim.

Two regressions these tests exist to catch, both of which I measured while
writing them:

* A leading lookahead does not guard a ``re.search`` row.  ``(?!...lines...)`` is
  evaluated at whatever position the match starts from, so "Which lines in the
  file X contain 'gamma'" still matched by starting at the word "file" --
  ``files?`` matches the singular -- and lost its line numbers.  The row is
  anchored with ``^`` so the lookahead reads the whole sentence.
* Keying ``-l`` on a content word alone stole "How many lines in the file X
  contain 'gamma'" away from the count it was measured to bind.

On ``90c8c84`` every test here fails except the three that pin behaviour which
must not change.
"""

import pathlib
import shutil
import sys
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime import composer_route_v1 as composer  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as admission  # noqa: E402

TEXT = "gamma"


class _Tree(unittest.TestCase):
    """One tree per test, removed by addCleanup.

    The directory is named for its content, never "test_something": path segments
    are query terms for the routing suites, so a scratch directory carrying that
    word would leak into any ranking measured in the same process.
    """

    _NEXT = 0

    def setUp(self):
        import os

        type(self)._NEXT += 1
        self.base = (
            _ROOT / "canonical/astra_runtime/tmp"
            / ("gammaq_%d_%d" % (os.getpid(), type(self)._NEXT))
        )
        (self.base / "sub").mkdir(parents=True)
        self.plain = self.base / "plain.txt"
        self.holder = self.base / "holder.txt"
        self.nested = self.base / "sub" / "nested.txt"
        self.plain.write_text("alpha\nbeta\n")
        self.holder.write_text("gamma ray\nsecond gamma\n")
        self.nested.write_text("gamma deep\n")
        self.addCleanup(shutil.rmtree, self.base, True)

    def solve(self, goal):
        # A unique task id per call: the admission front door keeps per-task
        # state, and reusing one id across sentences in the same process made
        # later answers come back empty.
        self._n = getattr(self, "_n", 0) + 1
        return admission.solve({"task_id": "GAMMAQ_%d" % self._n, "goal": goal})

    def answer(self, goal):
        out = self.solve(goal)
        steps = ((out.get("composer_execution") or {}).get("steps") or [{}])
        step = steps[0]
        argv = (step.get("args") or {}).get("argv") or []
        stdout = str((step.get("result") or {}).get("stdout") or "")
        return out, argv, stdout

    def rel(self):
        return str(self.base.relative_to(_ROOT))


class AnAbsolutePathKeepsItsLeadingSlashTests(_Tree):
    def test_the_directory_token_is_the_one_the_sentence_said(self):
        self.assertEqual(
            composer.extract_paths("List the directory %s" % self.base),
            [str(self.base)],
        )

    def test_a_relative_directory_is_unchanged(self):
        self.assertEqual(
            composer.extract_paths("List the directory %s" % self.rel()),
            [self.rel()],
        )

    def test_the_command_actually_runs_on_the_absolute_directory(self):
        out, argv, stdout = self.answer("List the directory %s" % self.base)
        self.assertIs(out.get("pass"), True, str(out.get("status")))
        self.assertEqual(argv[0], "ls")
        self.assertTrue(pathlib.Path(argv[-1]).is_absolute(), argv)
        self.assertEqual(sorted(stdout.split()), ["holder.txt", "plain.txt", "sub"])

    def test_an_absolute_file_and_an_absolute_directory_agree(self):
        """`_EXT` already kept the slash; `_DIRPATH` now does too."""
        for sentence in (
            "Count the lines in the file %s" % self.holder,
            "List the directory %s" % self.base,
        ):
            found = composer.extract_paths(sentence)
            self.assertTrue(found[0].startswith("/"), (sentence, found))


class WhichFilesHoldTheTextIsAnsweredByReadingThemTests(_Tree):
    def test_the_answer_is_exactly_the_files_that_hold_the_text(self):
        _, argv, stdout = self.answer(
            "Show which files in the directory %s contain '%s'" % (self.base, TEXT)
        )
        names = {pathlib.Path(line).name for line in stdout.split() if line}
        self.assertEqual(names, {"holder.txt", "nested.txt"})

    def test_a_file_that_does_not_hold_the_text_is_not_in_the_answer(self):
        """The falsification of `ls`: it lists plain.txt, which holds no gamma."""
        _, _, stdout = self.answer(
            "Show which files in the directory %s contain '%s'" % (self.base, TEXT)
        )
        self.assertNotIn("plain.txt", stdout)

    def test_the_nested_file_is_found_because_the_operand_is_a_directory(self):
        """The sentence never says "recursive"; the disk says it is a folder."""
        _, argv, stdout = self.answer(
            "Search the directory %s for '%s'" % (self.base, TEXT)
        )
        self.assertIn("-r", argv)
        self.assertIn("nested.txt", stdout)

    def test_two_spellings_of_one_question_give_one_answer(self):
        absolute = self.answer(
            "Show which files in the directory %s contain '%s'" % (self.base, TEXT)
        )[2]
        relative = self.answer(
            "Show which files in the directory %s contain '%s'" % (self.rel(), TEXT)
        )[2]
        def strip(answer, prefix):
            return {
                line[len(prefix):].lstrip("/")
                for line in answer.split()
                if line.startswith(prefix)
            }

        self.assertEqual(
            strip(absolute, str(self.base)), strip(relative, self.rel())
        )
        self.assertEqual(strip(absolute, str(self.base)),
                         {"holder.txt", "sub/nested.txt"})

    def test_three_phrasings_of_the_same_question_bind_one_operation(self):
        for sentence in (
            "Show which files in the directory %s contain '%s'" % (self.base, TEXT),
            "Which files in the directory %s hold the text '%s'" % (self.base, TEXT),
            "List the files in the directory %s containing '%s'" % (self.base, TEXT),
        ):
            _, argv, stdout = self.answer(sentence)
            self.assertEqual(argv[0], "grep", sentence)
            self.assertIn("-l", argv, sentence)
            self.assertNotIn("plain.txt", stdout, sentence)

    def test_a_directory_with_no_match_answers_nothing_not_everything(self):
        empty = self.base / "sub"
        _, argv, stdout = self.answer(
            "Show which files in the directory %s contain 'zzz_absent'" % empty
        )
        self.assertEqual(argv[0], "grep")
        self.assertEqual(stdout.strip(), "")


class APathThatContainsTheSearchedTextIsNotCorruptedTests(_Tree):
    """The fixture directory is named ``gammaq_...`` and the text is ``gamma``.

    That collision is the test, not an accident.  The value was masked by
    replacing its bare text everywhere in the sentence, so it was also blanked
    inside the path: the operand became ``.../tmp/ q_.../holder.txt``, which does
    not exist.  A repository whose own name is the word under search hits this on
    the first sentence it is ever asked.
    """

    def test_the_operand_is_the_path_the_sentence_named(self):
        _, argv, _ = self.answer(
            "Search the file %s for '%s'" % (self.holder, TEXT)
        )
        self.assertEqual(argv[-1], str(self.holder))

    def test_a_directory_operand_is_not_walked_one_level_up(self):
        _, argv, stdout = self.answer(
            "Show which files in the directory %s contain '%s'" % (self.base, TEXT)
        )
        self.assertEqual(argv[-1], str(self.base))
        self.assertNotIn("BSON", stdout)

    def test_the_answer_is_still_exactly_the_files_that_hold_the_text(self):
        _, _, stdout = self.answer(
            "Show which files in the directory %s contain '%s'" % (self.base, TEXT)
        )
        names = {pathlib.Path(line).name for line in stdout.split() if line}
        self.assertEqual(names, {"holder.txt", "nested.txt"})


class TheNounTheSentenceAsksAboutDecidesTheFlagsTests(_Tree):
    def test_a_question_about_lines_keeps_printing_lines(self):
        _, argv, stdout = self.answer(
            "Which lines in the file %s contain '%s'" % (self.holder, TEXT)
        )
        self.assertNotIn("-l", argv)
        self.assertIn("gamma ray", stdout)
        self.assertIn("1:", stdout)

    def test_a_count_of_matching_lines_is_still_a_count(self):
        _, argv, stdout = self.answer(
            "How many lines in the file %s contain '%s'" % (self.holder, TEXT)
        )
        self.assertIn("-c", argv)
        self.assertEqual(stdout.strip(), "2")

    def test_a_plain_listing_of_a_directory_is_still_a_listing(self):
        _, argv, stdout = self.answer("List the files in the directory %s" % self.base)
        self.assertEqual(argv[0], "ls")
        self.assertIn("plain.txt", stdout)

    def test_a_set_of_files_named_by_pattern_is_still_a_walk(self):
        _, argv, _ = self.answer(
            "List all the .txt files in the directory %s" % self.base
        )
        self.assertEqual(argv[0], "find")

    def test_one_file_is_never_searched_recursively(self):
        _, argv, stdout = self.answer(
            "Search the file %s for '%s'" % (self.holder, TEXT)
        )
        self.assertNotIn("-r", argv)
        self.assertEqual(stdout, "gamma ray\nsecond gamma\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
