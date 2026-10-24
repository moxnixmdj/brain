"""`tee` cannot be re-run to check it, so it is checked by what it left.

Re-running `tee A` is a second truncation, not a check -- the same reason cp, mv,
mkdir, touch and rm are judged by their effect rather than repeated. Measured on
44d995c: `tee A` created A correctly, the adapter fingerprinted it honestly
(0 bytes, output_verified True), and the request was still refused
COMMAND_NOT_RE_RUNNABLE_WITHOUT_SIDE_EFFECTS, because tee was the one command in
the everyday set with no postcondition.

What tee promises unconditionally is that its operand exists when it returns --
tee opens it with O_CREAT|O_TRUNC whatever is on stdin, including nothing. That
is checked here. What is deliberately NOT claimed is emptiness: that follows from
stdin, which this shape never sees, and a postcondition that asserted a fact about
a channel it never observed would be guessing.

A postcondition that only ever passes is not a check, so every accepting row below
is paired with the nearest world in which it must fail.
"""

import shutil
import unittest
from time import perf_counter_ns

from canonical.runtime import live_brain_route_admission_v1 as ra
import canonical.runtime.raw_goal_trace_acceptance_v1 as accept

ROOT = ra.ROOT
SCRATCH = "canonical/astra_runtime/tmp/tee1"


def _fresh(name):
    d = ROOT / ("%s/%s" % (SCRATCH, name))
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    return "%s/%s" % (SCRATCH, name)


def _solve(goal):
    return ra.solve({"task_id": "TE%d" % perf_counter_ns(), "goal": goal})


class TestASingleTeeIsCertifiedFromTheDisk(unittest.TestCase):

    def test_the_file_is_there_and_the_request_is_verified(self):
        base = _fresh("ok")
        dest = "%s/e1.txt" % base
        result = _solve("Run the shell command tee %s" % dest)
        self.assertTrue((ROOT / dest).is_file())
        self.assertTrue(
            str(result.get("status")).endswith("EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"),
            "not certified: %s / %s"
            % (result.get("status"), (result.get("raw_goal_acceptance") or {}).get("reason")),
        )

    def test_the_bytes_on_disk_are_the_bytes_the_adapter_fingerprinted(self):
        """Existence is not the only thing tying the file to the command."""
        import hashlib
        base = _fresh("bytes")
        dest = "%s/e2.txt" % base
        result = _solve("Run the shell command tee %s" % dest)
        steps = (result.get("composer_execution") or {}).get("steps") or []
        self.assertTrue(steps)
        claimed = (steps[0].get("result") or {}).get("output_sha256")
        self.assertEqual(
            hashlib.sha256((ROOT / dest).read_bytes()).hexdigest(), claimed,
            "the file on disk is not the file the producer fingerprinted",
        )


class TestThePromiseThatCannotBeStatedIsStillRefused(unittest.TestCase):

    def test_flags_make_the_shape_unstateable(self):
        for argv in (["tee", "-a", "x.txt"], ["tee", "--append", "x.txt"], ["tee", "-i", "x.txt"]):
            ok, reason, _ev = accept._post_tee(argv, ROOT)
            self.assertFalse(ok, "certified %r" % (argv,))
            self.assertEqual(reason, "COMMAND_TEE_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE")

    def test_two_operands_make_the_shape_unstateable(self):
        ok, reason, _ev = accept._post_tee(["tee", "a.txt", "b.txt"], ROOT)
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_TEE_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE")

    def test_a_bare_tee_with_no_operand_is_unstateable(self):
        ok, reason, _ev = accept._post_tee(["tee"], ROOT)
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_TEE_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE")

    def test_a_path_outside_the_repository_is_refused(self):
        ok, reason, _ev = accept._post_tee(["tee", "/etc/passwd"], ROOT)
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_TEE_PATH_OUTSIDE_REPOSITORY")

    def test_a_file_that_is_not_there_is_not_a_result(self):
        """The falsifier for the accepting row above."""
        base = _fresh("absent")
        ok, reason, _ev = accept._post_tee(["tee", "%s/never.txt" % base], ROOT)
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_TEE_TARGET_ABSENT_FROM_DISK")

    def test_a_directory_is_not_the_file_tee_promised(self):
        base = _fresh("dir")
        ok, reason, _ev = accept._post_tee(["tee", base], ROOT)
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_TEE_TARGET_ABSENT_FROM_DISK")


class TestTeeIsNotTreatedAsAConsumer(unittest.TestCase):

    def test_tee_produces_its_operand_so_it_excuses_nothing(self):
        """A producer must not borrow the excuse meant for a removal."""
        base = _fresh("producer")
        dest = "%s/e3.txt" % base
        (ROOT / dest).write_text("x\n", encoding="utf-8")
        self.assertNotIn("tee", accept._CONSUMES_AN_OPERAND)
        self.assertEqual(
            accept._verified_consumed_paths(
                {"argv": ["tee", dest], "output_path": dest}, ROOT),
            (),
        )


if __name__ == "__main__":
    unittest.main()
