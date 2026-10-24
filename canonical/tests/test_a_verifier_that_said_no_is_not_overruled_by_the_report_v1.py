"""Three ways the system said "done" over a check that said otherwise.

1. A sentence normally QUOTES the text it states.  Both anchors in
   _payload_runs_to_the_destination were written against unquoted sentences, so
   the role word had to run straight into the payload and the destination had to
   start the instant the payload ended.  Every quoting style failed.  Measured on
   a8d35d7: "Write the text 'hello there' to the file w.txt" wrote the correct 11
   bytes and was refused STEP_TEXT_PAYLOAD_NOT_IN_THE_REQUEST -- while solve()
   reported pass=True, because nothing downstream read that verdict.

2. "Absent from disk" is a claim about existence, and is_file() answers a
   different question too: it is False for a directory that is plainly there.
   mkdir created its directory and this layer called it absent.

3. A composed chain claimed pass=True on the strength of having run.  The verdict
   sitting beside it was never read, so the route ordinary sentences take was the
   one route that could outvote its own verifier.
"""

import shutil
import unittest
from time import perf_counter_ns

from canonical.runtime import live_brain_route_admission_v1 as ra
import canonical.runtime.raw_goal_trace_acceptance_v1 as accept

ROOT = ra.ROOT
SCRATCH = "canonical/astra_runtime/tmp/ver1"


def _fresh(name):
    d = ROOT / ("%s/%s" % (SCRATCH, name))
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    return "%s/%s" % (SCRATCH, name)


def _solve(goal):
    return ra.solve({"task_id": "VR%d" % perf_counter_ns(), "goal": goal})


class TestAQuotedPayloadIsThePayloadTheSentenceStated(unittest.TestCase):

    def test_every_quoting_style_reaches_the_destination(self):
        for quote in ("'", '"', "\u201c"):
            close = "\u201d" if quote == "\u201c" else quote
            goal = ("Write the text %shello there%s to the file c/x/w.txt"
                    % (quote, close))
            self.assertTrue(
                accept._payload_runs_to_the_destination(goal, "hello there"),
                "a %s-quoted payload was not recognised" % quote,
            )

    def test_a_truncated_payload_is_still_refused(self):
        """The defence this function exists for. It must survive the fix."""
        for goal, payload in (
            ("the results are in the attachment", "results are"),
            ("a plain sentence about nothing in particular",
             "plain sentence about nothing"),
            ("items in stock at the warehouse", "items"),
            ("text in the middle of it", "text"),
        ):
            self.assertFalse(
                accept._payload_runs_to_the_destination(goal, payload),
                "accepted a truncated payload: %r from %r" % (payload, goal),
            )

    def test_a_quoted_truncated_payload_is_still_refused(self):
        """Quoting must not become a way past the defence."""
        self.assertFalse(accept._payload_runs_to_the_destination(
            "the 'results are' in the attachment", "results are"))


class TestADirectoryIsNotReportedAbsentFromDisk(unittest.TestCase):

    def test_mkdir_is_verified_rather_than_called_absent(self):
        base = _fresh("mk")
        result = _solve("Run the shell command mkdir %s/sub" % base)
        self.assertTrue((ROOT / ("%s/sub" % base)).is_dir())
        self.assertIs(
            result.get("pass"), True,
            "refused a directory it created: %s" % (result.get("status"),),
        )
        acc = result.get("raw_goal_acceptance") or {}
        self.assertIsNot(
            acc.get("pass"), False,
            "verifier called an existing directory absent: %s" % (acc.get("reason"),),
        )


class TestAReportMayNotOutvoteItsVerifier(unittest.TestCase):

    def test_a_stated_write_is_verified_end_to_end(self):
        base = _fresh("w")
        dest = "%s/w.txt" % base
        result = _solve("Write the text 'hello there' to the file %s" % dest)
        self.assertEqual((ROOT / dest).read_text(encoding="utf-8"), "hello there")
        self.assertTrue(
            str(result.get("status")).endswith("EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"),
            "correct bytes but not certified: %s" % (result.get("status"),),
        )

    def test_no_composed_pass_survives_a_verifier_that_said_no(self):
        """The invariant, over every command in the everyday set."""
        cases = [
            "Run the shell command tee %s/e1.txt",
            "Run the shell command cat %s/a1.txt",
            "Run the shell command touch %s/t1.txt",
            "Run the shell command mkdir %s/sub",
        ]
        offenders = []
        for i, tmpl in enumerate(cases):
            base = _fresh("inv%d" % i)
            (ROOT / ("%s/a1.txt" % base)).write_text("alpha\n", encoding="utf-8")
            r = _solve(tmpl % base)
            acc = r.get("raw_goal_acceptance") or {}
            if r.get("pass") is True and acc.get("pass") is False:
                offenders.append((tmpl, acc.get("reason")))
        self.assertEqual(
            offenders, [],
            "%d commands reported pass=True over a verifier that said no" % len(offenders),
        )


if __name__ == "__main__":
    unittest.main()
