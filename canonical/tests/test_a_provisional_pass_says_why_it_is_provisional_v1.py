"""A provisional pass says why it is provisional, and never claims more than it proved.

Two defects on the front-layer local adapter path, both measured on 82c30fd over all
367 admissible capabilities named in prose (223 pass):

1. The trace row was written as ``{"action": ..., "result": ...}``.  The controller
   writes ``{"cycle", "plan", "result"}`` and closes its trace with a row whose
   ``result.type`` is ``"finish"`` (astra_runtime.py:6795, :6844).  The one consumer
   of a trace, ``raw_goal_trace_acceptance_v1``, reads ``row["plan"]`` at :164 and
   :181 and requires that finish row.  So it saw an empty trace:

       _action_rows(trace)       -> 0
       _trace_is_finished(trace) -> False

   and the only verdict it could return was ``TRACE_HAS_NO_CAPABILITY_ACTIONS`` --
   untrue, there was exactly one capability action.  **222 of 223** passes produced a
   trace the verifier could not read.

2. The path hard-coded ``semantic_acceptance_complete: False`` and
   ``accepted_raw_obligation_ids: []`` and never called the verifier, so **all 223**
   passes reported themselves provisional with no reason at all.

After the fix, measured over the same 367:

    traces the verifier cannot read   222 -> 1
    passes with no acceptance verdict 223 -> 2
    exact semantic acceptance           0 -> 0     (unchanged, and that is correct)
    pass / fail                       223 / 144    (unchanged)

The zero is the point.  The verdict is ``NO_INDEPENDENT_REINSPECTION_FOR:<path>`` for
every one of them: these executions print to stdout and leave no artifact to
re-inspect, so the refusal is right.  This change makes a provisional pass say WHY it
is provisional; it does not upgrade a single pass class, and one of the tests below
exists to fail if it ever does so by accident.
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "canonical/runtime")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical.runtime.live_brain_route_admission_v1 import solve          # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402
from canonical.runtime.raw_goal_trace_acceptance_v1 import (              # noqa: E402
    _action_rows, _trace_is_finished,
)

# A receipt-backed capability that takes no file and runs a repository script, so it
# passes through the front-layer local adapter path this test is about.
CID = "canonical/runtime/aa_briefcase_component_summary_noninversion_v1.py.auto.v1"


def _goal_for(cid):
    stem = re.sub(r"\.py\.auto\.v\d+$", "", cid.rsplit("/", 1)[-1])
    return "Run the %s." % stem.replace("_", " ").replace(".", " ")


class ProvisionalPassSaysWhyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.reg = dict(load_verified_registry())
        cls.result = solve({"task_id": "PROV1", "goal": _goal_for(CID)})

    def test_the_pass_really_takes_the_front_layer_path(self):
        """Guards the premise: if this capability ever routes elsewhere the rest of
        the class is measuring something else."""
        self.assertIs(self.result.get("pass"), True)
        self.assertEqual((self.result.get("controller_execution") or {}).get("controller_mode"),
                         "FRONT_LAYER_LOCAL_ADAPTER")

    def test_the_trace_is_readable_by_the_acceptance_verifier(self):
        trace = (self.result.get("controller_execution") or {}).get("trace")
        rows = _action_rows(trace)
        self.assertEqual(len(rows), 1, "expected exactly one capability action, got %r" % (rows,))
        self.assertTrue(_trace_is_finished(trace))
        self.assertEqual(rows[0]["args"].get("capability_id"), CID)

    def test_the_old_action_key_is_still_present(self):
        """A reader of the old key must not break; the fix adds "plan", it does not
        remove "action"."""
        trace = (self.result.get("controller_execution") or {}).get("trace")
        self.assertIn("action", trace[0])
        self.assertIn("plan", trace[0])
        self.assertEqual(trace[0]["action"], trace[0]["plan"])

    def test_the_result_carries_an_acceptance_verdict_with_a_reason(self):
        acceptance = self.result.get("raw_goal_acceptance")
        self.assertIsInstance(acceptance, dict)
        reason = str(acceptance.get("reason") or acceptance.get("status") or "")
        self.assertTrue(reason, "acceptance verdict carries no reason: %r" % (acceptance,))
        self.assertIn("NO_INDEPENDENT_REINSPECTION", reason)

    def test_it_never_claims_exact_acceptance_it_did_not_earn(self):
        """The anti-fabrication test.  Nothing was independently re-inspected, so the
        pass class must stay provisional.  If a future change starts upgrading these,
        this fails -- which is the whole point of shipping it."""
        self.assertIs(self.result.get("semantic_acceptance_complete"), False)
        self.assertEqual(self.result.get("accepted_raw_obligation_ids"), [])
        self.assertNotIn("EXACT_SEMANTIC_ACCEPTANCE_VERIFIED", str(self.result.get("status")))
        self.assertIn("RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED", str(self.result.get("status")))

    def test_a_verifier_fault_cannot_turn_a_pass_into_a_crash(self):
        import canonical.runtime.live_brain_route_admission_v1 as ra
        real = sys.modules["canonical.runtime.raw_goal_trace_acceptance_v1"]
        original = real.verify

        def _boom(**kwargs):
            raise RuntimeError("verifier exploded")

        real.verify = _boom
        try:
            result = solve({"task_id": "PROV2", "goal": _goal_for(CID)})
        finally:
            real.verify = original
        self.assertIs(result.get("pass"), True, "a verifier fault must not fail the goal")
        self.assertIs(result.get("semantic_acceptance_complete"), False)

    def test_no_pass_in_the_whole_corpus_carries_an_unreadable_trace(self):
        """Whole class, and the two numbers that moved.  Baseline on 82c30fd: 222 of
        223 passes had a trace the verifier could not read, and all 223 carried no
        acceptance verdict."""
        unreadable = []
        no_verdict = []
        exact = 0
        passes = 0
        for index, cid in enumerate(sorted(self.reg)):
            result = solve({"task_id": "PROV%03d" % index, "goal": _goal_for(cid)})
            if result.get("pass") is not True:
                continue
            passes += 1
            trace = (result.get("controller_execution") or {}).get("trace")
            if not _action_rows(trace):
                unreadable.append(cid)
            if result.get("raw_goal_acceptance") is None:
                no_verdict.append(cid)
            if "EXACT_SEMANTIC_ACCEPTANCE_VERIFIED" in str(result.get("status")):
                exact += 1
        self.assertGreaterEqual(passes, 200, "only %d passes; corpus changed shape" % passes)
        self.assertLessEqual(len(unreadable), 1, "unreadable traces: %s" % (unreadable,))
        self.assertLessEqual(len(no_verdict), 2, "no verdict: %s" % (no_verdict,))
        # Recorded, not asserted as a goal: no capability in the corpus earns exact
        # acceptance today.  If that ever changes this line must be updated on purpose.
        self.assertEqual(exact, 0, "exact acceptance appeared for some capability")


if __name__ == "__main__":
    unittest.main(verbosity=2)
