"""A command line the sentence states must run, and must be the one it stated.

``shell.command.run`` has been a ``VERIFIED_BOUND_CAPABILITY`` with an
independently verified output the whole time. Its adapter is careful: argv only,
no shell, cwd pinned to the repository root, timeout clamped to 1-300s, at most
64 non-empty string elements, and a non-zero exit raised rather than returned.

It was simply unreachable. ``bind`` had no rule for an ARGV slot, so every
sentence that named it was refused with ``shell.command.run:argv:not_stated``.
Measured on 2910d0b, 0 of 8 ordinary command requests ran. One slot type was the
entire distance between a verified general command runner and the requests that
would use it. After binding it: **7 of 8 run**, and they really run -- ``cp``
produces the copy, ``wc -l`` reports the real line count.

The half that makes this safe rather than merely powerful is the second file this
touches. An argv is a payload with teeth: it is executed, not written. So
``raw_goal_trace_acceptance_v1`` now re-derives the command from the sentence and
refuses a step whose argv the sentence does not contain, returning
``STEP_COMMAND_NOT_IN_THE_REQUEST``. Measured on the same real trace, an honest
goal reaches ``NO_INDEPENDENT_REINSPECTION_FOR:shell.command.run`` -- the argv
passed -- while the same trace replayed against a sentence asking for a different
command is stopped with the specific reason.

Two negative controls carry the weight here, because a general command runner is
exactly the kind of thing that must not be reachable by accident:

* ``extract_argv`` returns None for a sentence that states no command. That
  includes the shape of the entire regression corpus -- "Run the <capability>."
  -- none of which mentions "command" or "argv". Measured: the 367-prose corpus
  is unchanged at 223 pass / 144 fail with identical failure kinds.
* An unstated ARGV slot is left unbound and the composer says so. This is the
  rule PR #6119 established for a text slot: a slot filled from something the
  sentence does not contain is an invention, and an invention executes.
"""

from __future__ import annotations

import shutil
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RUNTIME = ROOT / "canonical" / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import canonical.runtime.composer_route_v1 as _binder  # noqa: E402

bind = _binder.bind

# Looked up rather than imported, so a tree without it yields failing assertions
# with a reason instead of a module-level ImportError that hides every check in
# this file.  On 2910d0b the binder had no ARGV rule at all, and that absence is
# the defect.
_EXTRACT_ARGV = getattr(_binder, "extract_argv", None)


def extract_argv(text: str):
    if _EXTRACT_ARGV is None:
        raise AssertionError(
            "composer_route_v1 has no way to take a command line from a sentence, "
            "so shell.command.run -- a VERIFIED_BOUND_CAPABILITY with an "
            "independently verified output -- is unreachable and every sentence "
            "that names it is refused with argv:not_stated."
        )
    return _EXTRACT_ARGV(text)

# No English words: every path component becomes a goal token, so a directory
# named for the behaviour under test can change which capability is selected.
SCRATCH = "canonical/astra_runtime/tmp/k4w7q"


def _solve(goal: str):
    from canonical.runtime.live_brain_route_admission_v1 import solve

    return solve({"task_id": "ARGV_%x" % time.perf_counter_ns(), "goal": goal})


def _fresh(content: str = "banana\napple\ncherry\n") -> str:
    root = ROOT / SCRATCH
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    f = "%s/a1.txt" % SCRATCH
    (ROOT / f).write_text(content, encoding="utf-8")
    return f


class TestTheStatedCommandLineIsTakenVerbatim(unittest.TestCase):
    CASES = (
        ("Run the shell command wc -l %s/a1.txt" % SCRATCH,
         ["wc", "-l", "%s/a1.txt" % SCRATCH]),
        ("Run the command cat %s/a1.txt" % SCRATCH,
         ["cat", "%s/a1.txt" % SCRATCH]),
        ("Run the shell command cp %s/a1.txt %s/b2.txt" % (SCRATCH, SCRATCH),
         ["cp", "%s/a1.txt" % SCRATCH, "%s/b2.txt" % SCRATCH]),
        ("Use the command line mv %s/a1.txt %s/b2.txt" % (SCRATCH, SCRATCH),
         ["mv", "%s/a1.txt" % SCRATCH, "%s/b2.txt" % SCRATCH]),
        ("Execute the shell command head -n 2 %s/a1.txt" % SCRATCH,
         ["head", "-n", "2", "%s/a1.txt" % SCRATCH]),
    )

    def test_every_stated_command_is_returned_token_for_token(self):
        wrong = [(g, extract_argv(g), want) for g, want in self.CASES
                 if extract_argv(g) != want]
        self.assertEqual(wrong, [], "argv not taken verbatim: %r" % wrong)


class TestNoCommandStatedNoCommandBound(unittest.TestCase):
    """The negative control that keeps a general runner from being reached by accident.

    Narrowed to the sentences that genuinely state no command, and made harder
    rather than softer.  The list this replaces also contained "Copy the file a
    to b", "Read the file a" and "Count the lines in the file a" -- which, once
    ordinary prose began to run, DO state a command.  Keeping them here would
    have turned the control into a ban on English.  What the control actually
    protects is the shape of the 367-sentence regression corpus: "Run the
    <capability>.", a sentence that names a capability and no action at all.
    Those three are still here, and nothing about them was relaxed.
    """

    # The regression corpus is 367 sentences of exactly this shape. If any of
    # them bound a command, a capability-naming sentence would execute one.
    NO_COMMAND = (
        "Run the archive manifest listing.",
        "Run the python source audit ast.",
        "Run the source candidates enumerate stdlib.",
        "Write the text hello world to the file %s/b2.txt" % SCRATCH,
        "Create the file %s/b2.txt containing the text second line" % SCRATCH,
    )

    # The other half, and the reason narrowing this list is not a weakening:
    # a sentence that DOES state a command must bind exactly the command it
    # stated.  The old file only ever checked that these bound nothing; now they
    # are pinned token by token, so a prose request that binds the wrong program
    # fails here instead of being quietly ignored.
    PROSE_COMMANDS = (
        ("Copy the file %s/a1.txt to %s/b2.txt" % (SCRATCH, SCRATCH),
         ["cp", "%s/a1.txt" % SCRATCH, "%s/b2.txt" % SCRATCH]),
        ("Move the file %s/a1.txt to %s/b2.txt" % (SCRATCH, SCRATCH),
         ["mv", "%s/a1.txt" % SCRATCH, "%s/b2.txt" % SCRATCH]),
        ("Remove the file %s/a1.txt" % SCRATCH,
         ["rm", "%s/a1.txt" % SCRATCH]),
        ("Create the directory %s/d9" % SCRATCH, ["mkdir", "%s/d9" % SCRATCH]),
        ("Create an empty file %s/e9" % SCRATCH, ["touch", "%s/e9" % SCRATCH]),
        ("Read the file %s/a1.txt" % SCRATCH, ["cat", "%s/a1.txt" % SCRATCH]),
        ("Count the lines in the file %s/a1.txt" % SCRATCH,
         ["wc", "-l", "%s/a1.txt" % SCRATCH]),
        ("Show the first 2 lines of the file %s/a1.txt" % SCRATCH,
         ["head", "-n", "2", "%s/a1.txt" % SCRATCH]),
        ("Sort the file %s/a1.txt" % SCRATCH, ["sort", "%s/a1.txt" % SCRATCH]),
        ("Compute the sha256 of the file %s/a1.txt" % SCRATCH,
         ["sha256sum", "%s/a1.txt" % SCRATCH]),
    )

    def test_a_sentence_that_states_no_command_binds_no_command(self):
        bound = [(g, extract_argv(g)) for g in self.NO_COMMAND if extract_argv(g)]
        self.assertEqual(bound, [], "invented a command line: %r" % bound)

    def test_every_prose_command_binds_the_command_it_stated(self):
        """Prose is not a licence to guess: each of these must bind exactly."""
        wrong = [(g, extract_argv(g), want) for g, want in self.PROSE_COMMANDS
                 if extract_argv(g) != want]
        self.assertEqual(wrong, [], "prose command not bound exactly: %r" % wrong)

    def test_a_prose_command_missing_an_operand_is_refused_not_completed(self):
        """The arity rule.  `cp` with one path must not invent a destination."""
        self.assertIsNone(extract_argv("Copy the file %s/a1.txt" % SCRATCH),
                          "invented the second operand of cp")

    def test_an_unstated_argv_slot_is_left_unbound(self):
        args = bind({"argv": "ARGV"}, "Run the archive manifest listing.")
        self.assertNotIn("argv", args, "bound an argv nobody stated: %r" % args)

    def test_a_stated_argv_does_bind(self):
        args = bind({"argv": "ARGV"}, "Run the shell command cat %s/a1.txt" % SCRATCH)
        self.assertEqual(args.get("argv"), ["cat", "%s/a1.txt" % SCRATCH])

    def test_a_prose_argv_binds_too(self):
        args = bind({"argv": "ARGV"}, "Read the file %s/a1.txt" % SCRATCH)
        self.assertEqual(args.get("argv"), ["cat", "%s/a1.txt" % SCRATCH])


class TestAStatedCommandReallyRuns(unittest.TestCase):
    """End to end, with the effect read back from disk rather than from a flag."""

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def test_a_stated_copy_produces_the_copy(self):
        f = _fresh()
        dest = "%s/b2.txt" % SCRATCH
        result = _solve("Run the shell command cp %s %s" % (f, dest))
        self.assertIs(result.get("pass"), True, "a stated command did not run: %r" % result.get("status"))
        self.assertTrue((ROOT / dest).is_file(), "cp ran but produced no copy")
        self.assertEqual((ROOT / dest).read_text(encoding="utf-8"), "banana\napple\ncherry\n")
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), "banana\napple\ncherry\n")

    def test_a_stated_line_count_reports_the_real_number(self):
        f = _fresh("one\ntwo\nthree\n")
        result = _solve("Run the shell command wc -l %s" % f)
        self.assertIs(result.get("pass"), True)
        steps = (result.get("composer_execution") or {}).get("steps") or []
        self.assertTrue(steps, "no step ran")
        stdout = str((steps[0].get("result") or {}).get("stdout") or "")
        self.assertIn("3", stdout, "wc -l did not report three lines: %r" % stdout)


class TestTheVerifierChecksTheCommandAgainstTheSentence(unittest.TestCase):
    """The half that makes reachability safe: the argv is re-derived, not trusted."""

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def _acceptance(self, goal: str, executed):
        from canonical.runtime import live_brain_route_admission_v1 as L

        return L._composed_acceptance(goal, ["shell.command.run"], executed)

    def test_an_argv_the_sentence_does_not_state_is_refused_by_name(self):
        f = _fresh()
        ran = _solve("Run the shell command cat %s" % f)
        executed = ran.get("composer_execution")
        self.assertIsInstance(executed, dict, "nothing ran to replay")
        verdict = self._acceptance("Run the shell command rm -rf %s" % SCRATCH, executed)
        reason = str((verdict.get("raw_goal_acceptance") or {}).get("reason") or "")
        self.assertEqual(
            reason,
            "STEP_COMMAND_NOT_IN_THE_REQUEST",
            "a command the sentence never stated was not refused by name; got %r" % reason,
        )

    def test_the_argv_a_sentence_stated_is_not_refused_as_unstated(self):
        """Guard must not fire on the honest case, or it proves nothing."""
        f = _fresh()
        ran = _solve("Run the shell command cat %s" % f)
        verdict = self._acceptance("Run the shell command cat %s" % f, ran.get("composer_execution"))
        reason = str((verdict.get("raw_goal_acceptance") or {}).get("reason") or "")
        self.assertNotEqual(
            reason,
            "STEP_COMMAND_NOT_IN_THE_REQUEST",
            "refused a command the sentence plainly states: %r" % reason,
        )


if __name__ == "__main__":
    unittest.main()
