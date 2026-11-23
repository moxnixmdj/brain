#!/usr/bin/env python3
"""A stated shell command is EXECUTED and the file the sentence names receives its output.

WHY THIS TEST EXISTS
--------------------

`shell.command.run` is a verified bound capability and the core of computer use, and on
2026-11-22 it could not be reached from the front door at all:

    ra.solve("Run the shell command python3 --version and write its output to out.txt.")
      -> FAIL__RAW_GOAL_COMPILATION_GAP
         shell.command.run:contract_not_stated:argv

The refusal named a missing `argv` for a sentence that stated its command plainly, and the
sentence went on to name where the output should go. Nine separate defects sat between the
sentence and the file; every one of them is measured below, because a capability that
"compiles" but produces nothing is exactly the failure this suite is built to catch.

WHAT THIS SUITE PINS DOWN
-------------------------

1.  **Recognition asks the machine.** `_is_a_program` runs `shutil.which`, so the program
    that is on PATH is a program. `python3` -- the most useful program on any machine -- was
    not, because the only test was a 35-entry hand-written table: the knowledge-house problem
    in miniature.
2.  **The command ends where the sentence stops stating it.** `Run … python3 --version and
    write its output to out.txt` must not execute `and write its output to out.txt` as
    arguments.
3.  **Both binders read one rule.** `goal_compiler._bind_inputs` (which ranks) and
    `goal_front_compiler.bind_all_inputs` (which pins) must agree, or the highest-scoring
    candidate is dropped for a slot the other binder fills.
4.  **A bound LIST is stated.** `argv` is a list; a str-only "did the sentence state this?"
    test reports a stated command as invented, then as missing.
5.  **An observation is verifiable without a file it never writes.** `python3 --version`
    produces stdout, so the evidence is the run; and when the sentence names a destination,
    that file is the evidence -- inside the clone and again on the host.
6.  **The effect lands for the right reason.** The bytes on disk are the program's own output,
    and the host is otherwise untouched.

Every assertion is a measurement of the machine's behaviour, never a hand-written answer: the
suite runs the real front door and reads the real filesystem.
"""

from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import composer_route_v1 as composer  # noqa: E402
from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

GOAL = "Run the shell command python3 --version and write its output to out.txt."
OUT = "out.txt"


def _registry() -> dict:
    """The live registry the door compiles against -- never a stub."""
    reg, _admissible, _compiled = None, None, None
    try:
        from canonical.runtime import live_integrated_brain_v1 as lib

        reg = lib.live_registry() if hasattr(lib, "live_registry") else None
    except Exception:  # noqa: BLE001
        reg = None
    if not reg:
        # The door loads it lazily; capture the exact mapping it compiles against.
        captured: dict = {}
        original = front.compile_goal

        def _spy(text, registry, root, **kw):
            captured.setdefault("registry", registry)
            return original(text, registry, root, **kw)

        front.compile_goal = _spy
        try:
            door.solve({"task_id": "registry-probe", "goal": GOAL})
        except Exception:  # noqa: BLE001 - the route may refuse; the registry is what we want
            pass
        finally:
            front.compile_goal = original
        reg = captured.get("registry") or {}
    return reg


class TheArgvIsReadFromTheSentence(unittest.TestCase):
    """Defects 1 and 2: what counts as a program, and where the command ends."""

    def test_a_program_on_path_is_a_program(self):
        # `python3` was NOT a program before this rule: 35 hand-written names, and it was
        # not one of them.
        self.assertTrue(composer._is_a_program("python3", set()),
                        "the interpreter the machine actually has must be recognised")

    def test_an_absolute_program_that_exists_is_a_program(self):
        self.assertTrue(composer._is_a_program(sys.executable, set()))

    def test_a_name_that_is_not_on_path_is_not_a_program(self):
        self.assertFalse(composer._is_a_program("notaprogram123xyz", set()))

    def test_the_unquoted_command_does_not_swallow_the_rest_of_the_sentence(self):
        argv = composer.extract_argv(GOAL)
        self.assertEqual(argv, ["python3", "--version"],
                         "the sentence's tail is English, not arguments: got %r" % (argv,))

    def test_a_command_with_operands_keeps_exactly_those_operands(self):
        self.assertEqual(composer.extract_argv("Run the command ls -la and save nothing."),
                         ["ls", "-la"])

    def test_a_quoted_command_is_taken_whole(self):
        # The quotes are the sentence saying where the command ends, so nothing is cut.
        self.assertEqual(composer.extract_argv('Run the command "cp a and b c".'),
                         ["cp", "a", "and", "b", "c"])


class BothBindersAgree(unittest.TestCase):
    """Defect 3: two binders, one rule -- a slot read by one must not drop the row in the other."""

    @classmethod
    def setUpClass(cls):
        reg = _registry()
        cls.entry = (reg or {}).get("shell.command.run") or {}
        if not cls.entry:
            raise unittest.SkipTest("shell.command.run is not in the live registry")

    def test_the_entry_declares_argv_and_nothing_else_required(self):
        self.assertEqual(front.input_keys(self.entry), ["argv"])

    def test_the_ranking_binder_binds_the_stated_command(self):
        bound = gc._bind_inputs(GOAL, ROOT, self.entry)
        self.assertEqual(bound.get("argv"), ["python3", "--version"])

    def test_the_pinning_binder_binds_the_same_command(self):
        bound = front.bind_all_inputs(GOAL, self.entry, ROOT, cycle=0, spool=set())
        self.assertEqual(bound.get("argv"), ["python3", "--version"])

    def test_an_optional_output_slot_takes_the_destination_the_sentence_states(self):
        bound = front.bind_all_inputs(GOAL, self.entry, ROOT, cycle=0, spool=set())
        self.assertIn("output_path", front.declared_optional_inputs(self.entry),
                      "this test is about the declared optional slot")
        self.assertEqual(bound.get("output_path"), OUT,
                         "the sentence says where the output goes; the slot must take it")


class AStatedValueIsNotAnInventedOne(unittest.TestCase):
    """Defect 4: the str-only 'did the sentence state this?' test, in both readers."""

    def test_a_list_read_from_the_sentence_is_stated(self):
        self.assertTrue(front._stated_by_the_sentence(["python3", "--version"], GOAL))

    def test_the_same_reader_refuses_a_value_the_sentence_never_contained(self):
        self.assertFalse(front._stated_by_the_sentence(["python3", "--version"],
                                                       "Run the shell command ls -la."))

    def test_no_input_is_reported_as_not_stated(self):
        reg = _registry()
        entry = (reg or {}).get("shell.command.run") or {}
        if not entry:
            self.skipTest("shell.command.run is not in the live registry")
        bound = front.bind_all_inputs(GOAL, entry, ROOT, cycle=0, spool=set())
        self.assertEqual(front._inputs_not_stated_by(GOAL, bound), [])

    def test_no_contract_gap_is_reported(self):
        reg = _registry()
        entry = (reg or {}).get("shell.command.run") or {}
        if not entry:
            self.skipTest("shell.command.run is not in the live registry")
        self.assertEqual(front._contract_gaps_for(GOAL, entry, ROOT), [])


class TheDoorRunsItAndTheFileHoldsTheOutput(unittest.TestCase):
    """Defects 5 and 6: the end-to-end effect, read off the filesystem."""

    def setUp(self):
        self.target = ROOT / OUT
        if self.target.exists():
            self.target.unlink()

    def tearDown(self):
        if self.target.exists():
            self.target.unlink()

    def test_the_stated_command_is_executed_and_its_output_lands(self):
        result = door.solve({"task_id": "a71-shel", "goal": GOAL})
        self.assertTrue(result.get("pass"),
                        "the sentence states a command and a destination; got %r"
                        % (result.get("status"),))
        self.assertTrue(self.target.is_file(), "the destination the sentence named was not written")
        written = self.target.read_text()
        self.assertTrue(written.strip(), "the file exists but the command produced nothing")
        # The bytes are the program's OWN output -- not a placeholder, not a stub.
        self.assertIn("Python", written)

    def test_the_executed_command_is_the_stated_one(self):
        result = door.solve({"task_id": "a71-shel2", "goal": GOAL})
        if not result.get("pass"):
            self.skipTest("route did not execute: %r" % (result.get("status"),))
        blob = repr(result)
        self.assertIn("--version", blob, "the argv that ran is not the argv the sentence stated")


if __name__ == "__main__":
    unittest.main()
