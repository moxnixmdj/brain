"""Fourteen everyday commands run, and each is verified by the world afterwards.

This suite exists because of a false alarm it would have prevented.  A ranking
change was believed to have taken the machine from fourteen everyday commands
working to one, and that belief was acted on -- a merge was blamed, and a
``git revert -m 1`` was run against a merge commit, which rewrote 14,797 files
before it was caught.  The belief was wrong: the measurement had silently changed
the SENTENCES, from "Run the shell command cp <a> <b>" to "Copy the file <a> to
<b>", which is a different and much harder input class that has never been
supported.  Nothing had regressed.

The mistake was possible because the fourteen commands were measured by an
ad-hoc probe that lived in nobody's test suite.  So the probe is the suite now.
Every row asserts three things at once: the request passed, the status ends in
EXACT_SEMANTIC_ACCEPTANCE_VERIFIED, and -- for the commands that must leave
something behind -- the thing is actually on disk.  A report that claims success
over an absent file fails here, which is the direction of error that matters.

Each mutating row is paired with the nearest world in which it must fail, in the
class below: the same command run against a path that cannot work has to be
refused rather than certified.
"""

import pathlib
import shutil
import tempfile
import time
import unittest

from canonical.runtime import live_brain_route_admission_v1 as ra

ROOT = ra.ROOT
BODY = "alpha\nbeta\ngamma\n"


class EverydayCommands(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(dir=ROOT / "canonical/astra_runtime/tmp"))
        self.a = self._w("a.txt", BODY)
        self.b = self._w("b.txt", "one\n")
        self.victim = self._w("victim.txt", "x")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _w(self, name, text):
        p = self.tmp / name
        p.write_text(text, encoding="utf-8")
        return str(p.relative_to(ROOT))

    def _solve(self, goal):
        return ra.solve({"task_id": "ev%d" % time.perf_counter_ns(), "goal": goal})

    def _exact(self, goal, produced=None):
        """Pass, exact semantic acceptance, and the promised thing on disk."""
        result = self._solve(goal)
        self.assertIs(result.get("pass"), True,
                      "%s did not pass: %s / %s" % (goal[:60], result.get("status"),
                                                    result.get("failure_class")))
        self.assertTrue(
            str(result.get("status")).endswith("EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"),
            "not exactly verified: %s (%s)" % (goal[:60], result.get("status")))
        if produced is not None:
            self.assertTrue((ROOT / produced).exists(),
                            "reported success but %s is not on disk" % produced)
        return result

    def test_the_read_commands_run_and_are_verified(self):
        for argv in ("cat %s", "wc -l %s", "head -n 2 %s", "grep beta %s",
                     "nl %s", "sha256sum %s", "sort %s"):
            self._exact("Run the shell command " + argv % self.a)

    def test_the_writing_commands_leave_the_file_they_promise(self):
        self._exact("Run the shell command tee %s" % str((self.tmp / "t.txt").relative_to(ROOT)),
                    str((self.tmp / "t.txt").relative_to(ROOT)))
        self._exact("Run the shell command touch %s" % str((self.tmp / "e.txt").relative_to(ROOT)),
                    str((self.tmp / "e.txt").relative_to(ROOT)))
        self._exact("Run the shell command mkdir %s" % str((self.tmp / "d1").relative_to(ROOT)),
                    str((self.tmp / "d1").relative_to(ROOT)))

    def test_copy_produces_a_copy_with_the_same_bytes(self):
        dest = str((self.tmp / "c.txt").relative_to(ROOT))
        self._exact("Run the shell command cp %s %s" % (self.a, dest), dest)
        self.assertEqual((ROOT / dest).read_text(encoding="utf-8"), BODY)

    def test_move_leaves_the_file_at_the_destination_and_not_at_the_source(self):
        dest = str((self.tmp / "m.txt").relative_to(ROOT))
        self._exact("Run the shell command mv %s %s" % (self.b, dest), dest)
        self.assertFalse((ROOT / self.b).exists(), "mv left the source behind")

    def test_remove_actually_removes(self):
        self._exact("Run the shell command rm %s" % self.victim)
        self.assertFalse((ROOT / self.victim).exists(),
                         "certified a removal but the file is still there")

    def test_a_stated_text_is_written_verbatim(self):
        out = str((self.tmp / "q.txt").relative_to(ROOT))
        self._exact("Write the text 'hello patch' to the file %s" % out, out)
        self.assertEqual((ROOT / out).read_text(encoding="utf-8"), "hello patch")


class TheNearestWorldInWhichEachMustFail(unittest.TestCase):
    """A suite that only accepts proves nothing. These are the refusals."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(dir=ROOT / "canonical/astra_runtime/tmp"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _solve(self, goal):
        return ra.solve({"task_id": "nv%d" % time.perf_counter_ns(), "goal": goal})

    def test_a_copy_whose_source_does_not_exist_is_not_certified(self):
        missing = str((self.tmp / "nope.txt").relative_to(ROOT))
        dest = str((self.tmp / "c.txt").relative_to(ROOT))
        result = self._solve("Run the shell command cp %s %s" % (missing, dest))
        self.assertIsNot(result.get("pass"), True,
                         "certified a copy from a source that was never there")

    def test_a_removal_of_something_absent_is_not_certified(self):
        absent = str((self.tmp / "ghost.txt").relative_to(ROOT))
        result = self._solve("Run the shell command rm %s" % absent)
        self.assertIsNot(result.get("pass"), True,
                         "certified the removal of a file that did not exist")

    def test_a_path_outside_the_repository_is_refused(self):
        result = self._solve("Run the shell command cat /etc/passwd")
        self.assertIsNot(result.get("pass"), True,
                         "read outside the repository and called it verified")


if __name__ == "__main__":
    unittest.main()
