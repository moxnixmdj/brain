"""A sentence containing the word "command" is not a command line.

Measured 2026-10-27 on main at afa82e5:

    solve("Repair the python source root D so the test command passes "
          "writing the report to D_out/r.json")

    capability_id  shell.command.run
    argv           ['passes', 'writing', 'the', 'report', 'to', 'D_out/r.json']
    adapter_raised FileNotFoundError:[Errno 2] No such file or directory: 'passes'
    failure_class  PROMISED_ARTIFACT_MISSING

The machine tried to EXECUTE THE REST OF THE SENTENCE AS A PROGRAM.  The cause
is in ``composer_route_v1._ARGV``: the role word is optional, so the pattern

    \\b(?:shell\\s+|cli\\s+|terminal\\s+)?command\\s+(?:to\\s+run\\s+|line\\s+)?(.+?)\\s*$

also matches the ordinary English noun in "the test command passes", and
everything after the noun becomes argv.  The front binder was never at fault --
``goal_front_compiler_v1`` already demands a quoted string for ``_ARGV_KEYS``.

The proof that an unquoted command line is a command line already existed in
this repository and was simply absent at this site: ``_prose_argv`` refuses any
program outside ``raw_goal_trace_acceptance_v1._READ_ONLY_COMMANDS`` and
``_MUTATING_POSTCONDITIONS``, and the adapter itself raises
``TEST_ARGS_WITHOUT_A_PROGRAM``.  A quoted command line needs no such proof --
the quotes are the sentence saying where the command ends -- which is why the
quoted form still wins and is asserted below.

Every test here fails on baseline: the first three because ``extract_argv``
returned prose there, the rest because ``_known_programs`` did not exist.
"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import composer_route_v1 as cr
from canonical.runtime import raw_goal_trace_acceptance_v1 as _accept


DEFECT = ("Repair the python source root /tmp/d so the test command passes "
          "writing the report to /tmp/d_out/r.json")


class ProseIsNotAProgramTests(unittest.TestCase):
    """The measured defect, and its nearest neighbours."""

    def test_the_word_command_followed_by_prose_is_not_a_command_line(self):
        self.assertIsNone(cr.extract_argv(DEFECT))

    def test_the_prose_that_used_to_become_argv_never_reaches_a_program(self):
        # Baseline returned exactly this.  Asserting the whole list, not just
        # that it is wrong, so a change that returns DIFFERENT prose still fails.
        self.assertIsNone(cr.extract_argv(DEFECT))
        baseline = ["passes", "writing", "the", "report", "to", "/tmp/d_out/r.json"]
        self.assertNotEqual(cr.extract_argv(DEFECT), baseline)

    def test_the_noun_in_a_question_is_not_a_command_line(self):
        for goal in ("Tell me whether the test command succeeds",
                     "Does the build command work?",
                     "Explain what the shell script command does",
                     "the test command for this repository is unknown to me"):
            with self.subTest(goal=goal):
                self.assertIsNone(cr.extract_argv(goal))

    def test_a_verb_after_the_noun_is_not_a_program(self):
        # "passes", "succeeds", "works", "fails" are what a test command DOES.
        # None of them is a program, and none may be executed.
        for verb in ("passes", "succeeds", "works", "fails", "runs"):
            with self.subTest(verb=verb):
                goal = ("Repair the python source root /tmp/d so the test "
                        "command %s and write the report to /tmp/d/r.json" % verb)
                self.assertIsNone(cr.extract_argv(goal))


class TheStatedCommandLineStillWorksTests(unittest.TestCase):
    """The nearest world in which the guard must NOT fire.

    A real command line, quoted or not, is the whole reason
    ``shell.command.run`` is reachable.  A guard that refuses those would turn a
    crash into a hole.
    """

    def test_an_unquoted_line_whose_first_token_is_a_program_is_a_command_line(self):
        self.assertEqual(cr.extract_argv("the command cp /a/b.txt /c/d.txt"),
                         ["cp", "/a/b.txt", "/c/d.txt"])

    def test_a_quoted_line_still_wins_over_the_prose_fallthrough(self):
        goal = ('Repair python bug in source /s/p.py with ast patch search guided '
                'by test /t/t.py using test command "python3 /t/t.py" and save '
                "output_path /o/r.json.")
        self.assertEqual(cr.extract_argv(goal), ["python3", "/t/t.py"])

    def test_a_quoted_line_needs_no_program_proof_at_all(self):
        # The quotes are the sentence telling us where the command ends.  A
        # quoted program outside the acceptance tables is the caller's own
        # content and must survive verbatim; only the UNQUOTED inference is a
        # guess that needs proving.
        self.assertEqual(cr.extract_argv('Run the shell command "mytool --go /a"'),
                         ["mytool", "--go", "/a"])

    def test_the_english_fallthrough_is_untouched(self):
        self.assertEqual(cr.extract_argv("Copy the file /a/b.txt to /c/d.txt"),
                         ["cp", "/a/b.txt", "/c/d.txt"])

    def test_a_malformed_command_line_is_still_refused_not_repaired(self):
        self.assertIsNone(cr.extract_argv('the command "cp /a /b'))


class TheProofIsTheAcceptanceLayersOwnTableTests(unittest.TestCase):
    """The guard must not carry a second copy of the program list."""

    def test_known_programs_is_the_union_of_the_two_existing_tables(self):
        self.assertEqual(
            cr._known_programs(),
            frozenset(_accept._READ_ONLY_COMMANDS) |
            frozenset(_accept._MUTATING_POSTCONDITIONS))

    def test_the_guard_reads_the_tables_it_does_not_restate_them(self):
        src = (REPO_ROOT / "canonical/runtime/composer_route_v1.py").read_text()
        # The defect class this whole file exists to prevent: a list written
        # twice is a list edited once.  The guard must import the acceptance
        # layer's tables rather than name programs of its own.
        head = src.split("def extract_argv(", 1)[1].split("\ndef ", 1)[0]
        self.assertNotIn('"cat"', head)
        self.assertNotIn('"cp"', head)
        self.assertIn("known", head)

    def test_every_program_the_prose_fallthrough_can_emit_is_known(self):
        for goal, expect in (("Copy the file /a/b.txt to /c/d.txt", "cp"),
                             ("Move the file /a/b.txt to /c/d.txt", "mv"),
                             ("Count the lines in the file /a/b.txt", "wc")):
            argv = cr.extract_argv(goal)
            if argv:
                with self.subTest(goal=goal):
                    self.assertEqual(argv[0], expect)
                    self.assertIn(argv[0], cr._known_programs())


if __name__ == "__main__":
    unittest.main()
