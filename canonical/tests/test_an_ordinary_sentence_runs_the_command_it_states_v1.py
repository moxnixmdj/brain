"""An ordinary sentence must run the command it states, and be checked for it.

``shell.command.run`` has been a ``VERIFIED_BOUND_CAPABILITY`` with an
independently verified output since PR #6120. Until now it was reachable only
from a sentence that QUOTED a command line -- "Run the shell command cp a b".
Phrased the way a person writes, "Copy the file a to b", it produced no argv at
all. Measured on ``0a87ba6``: **0 of 12** ordinary prose requests ran.

Three things had to change together, and each is pinned here:

1. A sentence stating a command in words yields that command's argv. Every
   program in the table is one the acceptance layer already knows how to judge
   afterwards, and an operand-count mismatch is refused rather than completed --
   an invented operand is an invented side effect.

2. ``solve`` falls through to a chain when the front compiler's selection was
   refused *and the sentence states a command line*. Measured on 0a87ba6, "Compute
   the sha256 of the file a1.txt" ranked ``shell.command.run`` FIRST at score 8,
   could not bind its argv from prose, moved on to ``finance.saccr.credit.addon.v1``
   on the single matched word "compute", and fail-closed that as
   ``R3_WEAK_EVIDENCE`` -- while the composer reached the request in one step.

3. ``sort -o B A`` gets a postcondition. Its promise is the strongest in the
   table because it needs no trust at all: the sorted bytes are recomputed from
   the source, which ``sort`` leaves on disk, and compared with the destination.

These tests read the effect back from the file system. They never trust ``pass``,
``status`` or any producer flag, because the defect classes this family keeps
finding are green verdicts over work that did not happen.
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

# No English words: every path component becomes a goal token, so a directory
# named for the behaviour under test can change which capability is selected.
SCRATCH = "canonical/astra_runtime/tmp/m3v7x"
UNSORTED = "banana\napple\ncherry\n"
SORTED = "apple\nbanana\ncherry\n"

extract_argv = getattr(_binder, "extract_argv", None)


def _argv(text: str):
    if extract_argv is None:
        raise AssertionError("composer_route_v1 has no extract_argv")
    return extract_argv(text)


def _fresh(content: str = UNSORTED) -> str:
    root = ROOT / SCRATCH
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    f = "%s/a1.txt" % SCRATCH
    (ROOT / f).write_text(content, encoding="utf-8")
    return f


def _solve(goal: str):
    from canonical.runtime.live_brain_route_admission_v1 import solve

    return solve({"task_id": "PROSE_%x" % time.perf_counter_ns(), "goal": goal})


def _verified(result) -> bool:
    """Accepted, and accepted for the right reason."""
    return (result.get("pass") is True
            and (result.get("raw_goal_acceptance") or {}).get("pass") is True
            and str(result.get("status") or "").endswith(
                "EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"))


class TestAnOrdinarySentenceYieldsTheCommandItStates(unittest.TestCase):
    """Half one: the words become the argv, token for token, or nothing."""

    CASES = (
        ("Copy the file {f} to {g}", ["cp", "{f}", "{g}"]),
        ("Move the file {f} to {g}", ["mv", "{f}", "{g}"]),
        ("Remove the file {f}", ["rm", "{f}"]),
        ("Create the directory {d}", ["mkdir", "{d}"]),
        ("Create an empty file {e}", ["touch", "{e}"]),
        ("Read the file {f}", ["cat", "{f}"]),
        ("Count the lines in the file {f}", ["wc", "-l", "{f}"]),
        ("Show the first 2 lines of the file {f}", ["head", "-n", "2", "{f}"]),
        ("Sort the file {f}", ["sort", "{f}"]),
        ("Compute the sha256 of the file {f}", ["sha256sum", "{f}"]),
        # The destination is not the last operand here: sort writes through -o.
        ("Sort the file {f} into {g}", ["sort", "-o", "{g}", "{f}"]),
    )

    SUBS = (("{f}", "%s/a1.txt" % SCRATCH), ("{g}", "%s/b2.txt" % SCRATCH),
            ("{d}", "%s/d9" % SCRATCH), ("{e}", "%s/e9" % SCRATCH))

    def _fmt(self, argv):
        out = []
        for part in argv:
            for needle, value in self.SUBS:
                part = part.replace(needle, value)
            out.append(part)
        return out

    def test_every_prose_command_binds_the_command_it_stated(self):
        wrong = []
        for template, want in self.CASES:
            goal = self._fmt([template])[0]
            got = _argv(goal)
            if got != self._fmt(want):
                wrong.append((template, got, self._fmt(want)))
        self.assertEqual(wrong, [], "prose command not bound exactly: %r" % wrong)

    def test_a_command_missing_an_operand_is_refused_not_completed(self):
        """The arity rule. cp with one path must not invent a destination."""
        self.assertIsNone(_argv("Copy the file %s/a1.txt" % SCRATCH),
                          "invented the second operand of cp")
        self.assertIsNone(_argv("Move the file %s/a1.txt" % SCRATCH),
                          "invented the second operand of mv")

    def test_a_sentence_that_states_no_command_binds_no_command(self):
        """The negative control that keeps a general runner out of reach."""
        for goal in ("Check the file %s/a1.txt" % SCRATCH,
                     "Run the archive manifest listing.",
                     "Run the python source audit ast.",
                     "Write the text hello world to the file %s/b2.txt" % SCRATCH):
            self.assertIsNone(_argv(goal), "invented a command line for %r" % goal)


class TestEveryProseRequestRunsAndIsChecked(unittest.TestCase):
    """Half two, end to end, with the effect read back from disk."""

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def _run(self, goal: str):
        return _solve(goal)

    def test_a_stated_copy_leaves_both_files(self):
        f = _fresh()
        g = "%s/b2.txt" % SCRATCH
        result = self._run("Copy the file %s to %s" % (f, g))
        self.assertTrue(_verified(result), "a stated copy was not verified: %r"
                        % result.get("status"))
        self.assertEqual((ROOT / g).read_text(encoding="utf-8"), UNSORTED)
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), UNSORTED)

    def test_a_stated_move_leaves_only_the_destination(self):
        f = _fresh()
        g = "%s/b2.txt" % SCRATCH
        result = self._run("Move the file %s to %s" % (f, g))
        self.assertTrue(_verified(result), "a stated move was not verified: %r"
                        % result.get("status"))
        self.assertFalse((ROOT / f).exists(), "the source survived a move")
        self.assertEqual((ROOT / g).read_text(encoding="utf-8"), UNSORTED)

    def test_a_stated_removal_really_removes(self):
        f = _fresh()
        result = self._run("Remove the file %s" % f)
        self.assertTrue(_verified(result), "a stated removal was not verified: %r"
                        % result.get("status"))
        self.assertFalse((ROOT / f).exists(), "the file survived its own removal")

    def test_a_stated_directory_is_a_real_directory(self):
        _fresh()
        d = "%s/d9" % SCRATCH
        result = self._run("Create the directory %s" % d)
        self.assertTrue(_verified(result), "a stated mkdir was not verified: %r"
                        % result.get("status"))
        self.assertTrue((ROOT / d).is_dir(), "mkdir was verified over no directory")

    def test_a_stated_empty_file_is_empty(self):
        _fresh()
        e = "%s/e9" % SCRATCH
        result = self._run("Create an empty file %s" % e)
        self.assertTrue(_verified(result), "a stated touch was not verified: %r"
                        % result.get("status"))
        self.assertTrue((ROOT / e).is_file())
        self.assertEqual((ROOT / e).read_text(encoding="utf-8"), "",
                         "the file the sentence called empty was not empty")

    def test_a_stated_read_leaves_the_file_alone(self):
        f = _fresh()
        result = self._run("Read the file %s" % f)
        self.assertTrue(_verified(result), "a stated read was not verified: %r"
                        % result.get("status"))
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), UNSORTED)

    def test_a_stated_line_count_reports_the_real_number(self):
        f = _fresh()
        result = self._run("Count the lines in the file %s" % f)
        self.assertTrue(_verified(result), "a stated wc -l was not verified: %r"
                        % result.get("status"))
        steps = (result.get("composer_execution") or {}).get("steps") or []
        self.assertTrue(steps, "no step ran")
        self.assertIn("3", str((steps[0].get("result") or {}).get("stdout") or ""),
                      "wc -l did not report three lines")

    def test_the_first_two_lines_are_the_first_two_lines(self):
        f = _fresh()
        result = self._run("Show the first 2 lines of the file %s" % f)
        self.assertTrue(_verified(result), "a stated head was not verified: %r"
                        % result.get("status"))
        steps = (result.get("composer_execution") or {}).get("steps") or []
        out = str((steps[0].get("result") or {}).get("stdout") or "")
        self.assertEqual(out.strip().splitlines(), ["banana", "apple"],
                         "head -n 2 did not return the first two lines: %r" % out)

    def test_a_stated_sort_to_stdout_leaves_the_file(self):
        f = _fresh()
        result = self._run("Sort the file %s" % f)
        self.assertTrue(_verified(result), "a stated sort was not verified: %r"
                        % result.get("status"))
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), UNSORTED,
                         "a sort to stdout rewrote its own input")

    def test_a_stated_checksum_runs(self):
        f = _fresh()
        result = self._run("Compute the sha256 of the file %s" % f)
        self.assertTrue(_verified(result), "a stated sha256sum was not verified: %r"
                        % result.get("status"))
        steps = (result.get("composer_execution") or {}).get("steps") or []
        out = str((steps[0].get("result") or {}).get("stdout") or "")
        self.assertEqual(len(out.split()[0]) if out.split() else 0, 64,
                         "sha256sum did not report a digest: %r" % out)
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), UNSORTED)

    def test_a_stated_sort_into_a_file_writes_the_sorted_bytes_there(self):
        """The strongest row: the promise is recomputed, not trusted."""
        f = _fresh()
        g = "%s/b2.txt" % SCRATCH
        result = self._run("Sort the file %s into %s" % (f, g))
        self.assertTrue(_verified(result), "a stated sort -o was not verified: %r"
                        % result.get("status"))
        self.assertEqual((ROOT / g).read_text(encoding="utf-8"), SORTED,
                         "the destination is not the source in order")
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), UNSORTED,
                         "sorting into a file consumed the source")


class TestTheSortPostconditionIsAnOracleNotATrust(unittest.TestCase):
    """The half that makes ``sort -o`` safe: it is judged against the disk."""

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def _accept(self, argv):
        from canonical.runtime import raw_goal_trace_acceptance_v1 as A

        return A._inspect_shell_command_run({"argv": list(argv)}, {}, ROOT)

    def test_a_destination_that_is_not_the_source_in_order_is_refused(self):
        _fresh()
        (ROOT / ("%s/b2.txt" % SCRATCH)).write_text(UNSORTED, encoding="utf-8")
        ok, reason, _ = self._accept(
            ["sort", "-o", "%s/b2.txt" % SCRATCH, "%s/a1.txt" % SCRATCH])
        self.assertIs(ok, False, "certified a destination that is not sorted")
        self.assertEqual(reason, "COMMAND_SORT_DESTINATION_IS_NOT_THE_SOURCE_IN_ORDER")

    def test_a_sorted_destination_is_accepted(self):
        _fresh()
        (ROOT / ("%s/b2.txt" % SCRATCH)).write_text(SORTED, encoding="utf-8")
        ok, reason, _ = self._accept(
            ["sort", "-o", "%s/b2.txt" % SCRATCH, "%s/a1.txt" % SCRATCH])
        self.assertIs(ok, True, "refused a destination that is exactly sorted: %s" % reason)

    def test_an_absent_source_is_refused(self):
        _fresh()
        ok, reason, _ = self._accept(
            ["sort", "-o", "%s/b2.txt" % SCRATCH, "%s/absent.txt" % SCRATCH])
        self.assertIs(ok, False)
        self.assertEqual(reason, "COMMAND_SORT_SOURCE_ABSENT_FROM_DISK")

    def test_shapes_whose_promise_cannot_be_stated_are_refused(self):
        _fresh()
        # NOTE: ["sort", "<file>"] is deliberately absent. With no -o it writes
        # nothing, so it stays a reader and is checked by re-running it -- that
        # is row nine of the passing table above, not a shape to refuse.
        for argv in (["sort", "-o", "%s/b2.txt" % SCRATCH],
                     ["sort", "-o", "%s/b2.txt" % SCRATCH, "%s/a1.txt" % SCRATCH,
                      "%s/a1.txt" % SCRATCH]):
            ok, reason, _ = self._accept(argv)
            self.assertIs(ok, False, "certified an unstateable shape: %r" % argv)
            self.assertIn("UNSTATEABLE", reason,
                          "the refusal does not say why: %r for %r" % (reason, argv))

    def test_an_output_flag_with_no_postcondition_is_still_refused(self):
        """The guard on the widening: only sort gained a promise.

        ``grep -o`` means only-matching, not output-to-file, and there is no
        postcondition for it. It must be refused exactly as it was before the
        branch order changed, never re-run.
        """
        _fresh()
        ok, reason, _ = self._accept(
            ["grep", "-o", "apple", "%s/a1.txt" % SCRATCH])
        self.assertIs(ok, False, "re-ran a command whose -o is not an output flag")
        self.assertEqual(reason, "COMMAND_TAKES_AN_OUTPUT_FLAG")


class TestTheFallthroughIsScopedToWhatTheSentenceStates(unittest.TestCase):
    """The #6119 hazard the widened fallthrough must not reopen."""

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def test_a_sentence_stating_neither_payload_nor_command_still_fails_closed(self):
        """'Check the file X' states nothing to compose. It must not write."""
        f = _fresh("PRECIOUS ORIGINAL CONTENT\n")
        self.assertIsNone(_argv("Check the file %s" % f))
        result = _solve("Check the file %s" % f)
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"),
                         "PRECIOUS ORIGINAL CONTENT\n",
                         "a request that stated nothing changed the file")
        self.assertIsNot(result.get("pass"), True,
                         "reported pass=True over a request that stated nothing")


if __name__ == "__main__":
    unittest.main()
