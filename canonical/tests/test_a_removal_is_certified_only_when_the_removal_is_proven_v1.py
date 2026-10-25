"""`rm` is certified by proving the file is gone -- never by assuming it.

Three excuses were added to the acceptance layer to let a removal through, and
each one is a hole unless it is earned:

  * a path may be reported absent when a verified postcondition names it as the
    path the command consumed;
  * a producer that says output_verified False is excused for that same path,
    because a command that removed its output has nothing to fingerprint;
  * the adapter records the absence instead of raising, but only on the caller's
    explicit word, and only for a command the postcondition table knows.

Every one of them is granted by a check that looked at the disk.  These tests are
the other half: the shapes where the promise cannot be stated, and the worlds
where the check does not pass, must still refuse.
"""

import shutil
import unittest
from time import perf_counter_ns

from canonical.runtime import live_brain_route_admission_v1 as ra
import canonical.runtime.raw_goal_trace_acceptance_v1 as accept

ROOT = ra.ROOT
SCRATCH = "canonical/astra_runtime/tmp/rmc1"


def _fresh(name):
    d = ROOT / ("%s/%s" % (SCRATCH, name))
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    return "%s/%s" % (SCRATCH, name)


def _solve(goal):
    return ra.solve({"task_id": "RM%d" % perf_counter_ns(), "goal": goal})


class TestASingleRemovalIsCertifiedFromTheDisk(unittest.TestCase):

    def test_the_file_is_gone_and_the_removal_is_verified(self):
        base = _fresh("ok")
        target = "%s/a1.txt" % base
        (ROOT / target).write_text("doomed\n", encoding="utf-8")
        result = _solve("Run the shell command rm %s" % target)
        self.assertFalse((ROOT / target).exists())
        self.assertTrue(
            str(result.get("status")).endswith("EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"),
            "removal not certified: %s / %s"
            % (result.get("status"), (result.get("raw_goal_acceptance") or {}).get("reason")),
        )


class TestThePromiseThatCannotBeStatedIsStillRefused(unittest.TestCase):

    def test_flags_make_the_shape_unstateable(self):
        # Rewritten, not deleted.  `-r` used to be in this list and is not any
        # more: it changes only WHETHER a directory may be removed, not WHAT is
        # promised, and "Delete the directory D" measured as binding plain `rm D`,
        # failing on a directory that was not empty, and reporting
        # COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN -- the vaguest report there is.
        # `-f` stays, and stays for a concrete reason: it suppresses the error
        # that is the only evidence a named path was ever there.
        for argv in (["rm", "-f", "x.txt"], ["rm", "--", "x.txt"],
                     ["rm", "-rf", "x.txt"], ["rm", "-i", "x.txt"],
                     ["rm", "-r", "-f", "x.txt"]):
            ok, reason, _ev = accept._post_rm(argv, ROOT)
            self.assertFalse(ok, "certified %r" % (argv,))
            self.assertEqual(reason, "COMMAND_RM_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE")

    def test_a_flag_makes_the_shape_unstateable_however_many_operands_follow(self):
        # What the old two-operand refusal was really about, kept and widened:
        # a flag changes what `rm` does, and the promise this table can state
        # does not cover it.  Two plain operands are stateable now -- a sentence
        # may name a set -- so the pin is on the flag, not on the count.
        base = _fresh("still")
        gone = "%s/gone.txt" % base
        for argv in (["rm", "-f", gone], ["rm", "--", gone],
                     ["rm", "-f", gone, "%s/other.txt" % base]):
            ok, reason, _ev = accept._post_rm(argv, ROOT)
            self.assertFalse(ok, argv)
            self.assertEqual(reason, "COMMAND_RM_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", argv)

    def test_the_recursive_flag_is_stateable_and_still_has_to_prove_itself(self):
        # The other side of the change above, pinned from both directions so it
        # cannot pass by simply trusting the flag.  A directory that is really
        # gone is certified; a directory that SURVIVED is refused, which is the
        # whole reason the check exists.
        base = _fresh("still")
        survivor = "%s/stillhere" % base
        (ROOT / survivor).mkdir(parents=True, exist_ok=True)
        ok, reason, _ev = accept._post_rm(["rm", "-r", survivor], ROOT)
        self.assertFalse(ok, "a surviving directory was certified as removed")
        self.assertEqual(reason, "COMMAND_RM_TARGET_STILL_PRESENT")
        (ROOT / survivor).rmdir()
        ok, _reason, ev = accept._post_rm(["rm", "-r", survivor], ROOT)
        self.assertTrue(ok)
        self.assertIn(survivor, ev.get("consumed_paths") or ())

    def test_every_operand_is_judged_not_just_the_first(self):
        # The multi-operand shape is only honest if each operand is checked on
        # its own: one survivor out of two is a removal that did not happen, and
        # an outside path slipped into the third position must be caught even
        # though the first two are inside the repository and gone.
        base = _fresh("still")
        first = "%s/first.txt" % base
        second = "%s/second.txt" % base
        (ROOT / first).write_text("x\n", encoding="utf-8")
        (ROOT / second).write_text("y\n", encoding="utf-8")
        (ROOT / first).unlink()
        ok, reason, ev = accept._post_rm(["rm", first, second], ROOT)
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_RM_TARGET_STILL_PRESENT")
        self.assertEqual(second, ev.get("survivor"))
        (ROOT / second).unlink()
        ok, reason, ev = accept._post_rm(["rm", first, second], ROOT)
        self.assertTrue(ok, reason)
        self.assertEqual(sorted([first, second]), sorted(ev["consumed_paths"]))
        ok, reason, _ev = accept._post_rm(["rm", first, second, "/etc/passwd"], ROOT)
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_RM_PATH_OUTSIDE_REPOSITORY")

    def test_a_path_outside_the_repository_is_refused(self):
        ok, reason, _ev = accept._post_rm(["rm", "/etc/passwd"], ROOT)
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_RM_PATH_OUTSIDE_REPOSITORY")

    def test_a_file_that_is_still_there_is_not_a_removal(self):
        base = _fresh("still")
        target = "%s/keep.txt" % base
        (ROOT / target).write_text("still here\n", encoding="utf-8")
        ok, reason, _ev = accept._post_rm(["rm", target], ROOT)
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_RM_TARGET_STILL_PRESENT")
        self.assertTrue((ROOT / target).exists(), "the probe deleted the file")


class TestTheExcuseIsEarnedAndNotAssumed(unittest.TestCase):

    def test_no_path_is_excused_when_the_postcondition_fails(self):
        """The whole safety of the skip lives here."""
        base = _fresh("unearned")
        target = "%s/keep.txt" % base
        (ROOT / target).write_text("still here\n", encoding="utf-8")
        self.assertEqual(
            accept._verified_consumed_paths(
                {"argv": ["rm", target], "output_path": target}, ROOT),
            (),
            "excused a path whose removal was never proven",
        )

    def test_a_path_is_excused_only_once_the_removal_is_proven(self):
        base = _fresh("earned")
        target = "%s/gone.txt" % base
        self.assertEqual(
            accept._verified_consumed_paths(
                {"argv": ["rm", target], "output_path": target}, ROOT),
            (target,),
        )

    def test_an_unknown_command_excuses_nothing(self):
        base = _fresh("unknown")
        target = "%s/x.txt" % base
        self.assertEqual(
            accept._verified_consumed_paths(
                {"argv": ["shred", target], "output_path": target}, ROOT),
            (),
        )

    def test_every_declared_consumer_really_reports_what_it_consumed(self):
        """Pins _CONSUMES_AN_OPERAND to the postcondition table."""
        for program in sorted(accept._CONSUMES_AN_OPERAND):
            check = accept._MUTATING_POSTCONDITIONS.get(program)
            self.assertIsNotNone(check, "%s declared a consumer with no postcondition" % program)
            base = _fresh("pin_%s" % program)
            if program == "rm":
                argv = ["rm", "%s/g.txt" % base]
            elif program == "gzip":
                # gzip leaves the source gone and a COMPLETE archive in its
                # place, so that is the world the promise is asked about -- and
                # writing it through gzip.compress means the stream really does
                # carry the source's bytes and a valid CRC.
                import gzip as _gzip
                with _gzip.open("%s/g.txt.gz" % base if False else
                                str(ROOT / ("%s/g.txt.gz" % base)), "wb") as handle:
                    handle.write(b"pin_gzip\n")
                argv = ["gzip", "%s/g.txt" % base]
            else:
                # A postcondition judges the WORLD, it does not run anything, so
                # the world has to be put in the state the command would have
                # left it in before the promise can be asked about.
                (ROOT / ("%s/d.txt" % base)).write_text("x\n", encoding="utf-8")
                argv = ["mv", "%s/s.txt" % base, "%s/d.txt" % base]
            ok, _reason, evidence = check(argv, ROOT)
            self.assertTrue(ok, "%s postcondition did not pass on its own happy path" % program)
            self.assertTrue(
                (evidence or {}).get("consumed_paths"),
                "%s is declared a consumer but reports no consumed path" % program,
            )


if __name__ == "__main__":
    unittest.main()
