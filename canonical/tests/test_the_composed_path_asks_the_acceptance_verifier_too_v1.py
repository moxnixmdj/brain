"""The route a natural sentence takes must be checked like every other route.

A sentence that names no capability -- "Write the text hello to the file
notes.txt" -- matches no single capability, so the composer answers it with a
chain.  That path reported `pass: True` on the strength of the chain having run,
with no acceptance verdict of any kind.  The front-layer local adapter path was
fixed in PR #6111 and the model-independent controller path in #6112; this was
the third and last path that never asked, and it is the one ordinary requests
actually take.

It could not ask before, for two concrete reasons:

  * the composer's step records were `{"raw": null}`, so there was no evidence
    to inspect (fixed in PR #6115);
  * no acceptance contract was ever built on this path.  `compile_contract`
    derives one from the sentence alone, but refuses with
    ROUTING_TARGET_EFFECTS_EMPTY unless it is told which files the request
    touches.  Measured on the same sentence: 0 obligations with an empty effect
    set, 2 with the step's own `output_path`.

And `text.file.write` -- the capability those sentences reach -- had no
re-inspector, so the verifier would have refused it with
NO_INDEPENDENT_REINSPECTION_FOR:text.file.write even given a contract.

Measured over six natural-language goals, before and after:

    BEFORE  pass 5 of 6, exact semantic acceptance 1 of 6
    AFTER   pass 5 of 6, exact semantic acceptance 5 of 6

The four that changed are the four that write a text file.  Over all 367
admissible capabilities driven from prose: pass 223 / fail 144 and failure kinds
CONTRACT_REFUSAL 138 / ENVIRONMENT_BLOCKER 3 / UNKNOWN 3, all unchanged.

The inspector re-derives the expected bytes from the REQUEST (`args["content"]`)
and compares them to the file on disk.  It does not consult `output_verified` or
`output_sha256`: both only prove the file is what the writer wrote, not that it
is what was asked for.  Tests 2 and 3 are the negative controls that make that
claim testable -- a file with the wrong bytes and a file that is absent must
both be refused.
"""

from __future__ import annotations

import hashlib
import pathlib
import shutil
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "canonical" / "runtime") not in sys.path:
    sys.path.insert(0, str(ROOT / "canonical" / "runtime"))

import canonical.runtime.raw_goal_trace_acceptance_v1 as acceptance  # noqa: E402
from canonical.runtime.live_brain_route_admission_v1 import solve  # noqa: E402

# A dedicated directory that is EMPTIED before these tests run.  Measured, this
# matters: files an earlier probe left in a shared scratch directory change what
# the goal compiler selects, and the same sentence that reached exact acceptance
# in an empty directory was refused with FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
# once that directory held a dozen artifacts.  A test that depends on the state
# of a shared directory is not a reproducible measurement.
_DIRNAME = "composed_acceptance_v1"
_REL = "canonical/astra_runtime/tmp/" + _DIRNAME


class TestTheComposedPathAsksTheAcceptanceVerifierTooV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        shutil.rmtree(ROOT / _REL, ignore_errors=True)
        (ROOT / _REL).mkdir(parents=True, exist_ok=True)

    def _fresh_rel(self, tag: str) -> str:
        """A repository-relative directory that is empty when it is returned.

        The two end-to-end tests must not share a directory with the inspector
        tests above: files already present change what the goal compiler selects,
        and a sentence that reaches exact acceptance against an empty directory
        is refused with FAIL_CLOSED__ROUTE_ADMISSION_REJECTED against a directory
        holding a dozen artifacts.  Measured, not assumed.
        """
        # The directory name is deliberately free of dictionary words.  Measured:
        # a directory called composed_acceptance_e2e makes the SAME sentence fail
        # with FAIL_CLOSED__ROUTE_ADMISSION_REJECTED, because the path's own
        # components become goal tokens and match capability names, while
        # cav1e2e, q7x2e2e and scratch_a1 all reach exact acceptance.  A fixture
        # whose NAME changes the verdict is not a fixture.
        rel = "canonical/astra_runtime/tmp/cav1_%s_%x" % (
            tag, time.perf_counter_ns())
        absolute = ROOT / rel
        shutil.rmtree(absolute, ignore_errors=True)
        absolute.mkdir(parents=True, exist_ok=True)
        return rel

    # ---- the inspector itself -------------------------------------------

    def test_the_capability_that_writes_text_has_a_re_inspector(self) -> None:
        self.assertIn("text.file.write", acceptance.INSPECTORS)

    def test_a_file_whose_bytes_are_not_the_requested_text_is_refused(self) -> None:
        """Negative control: the inspector must be able to say no."""
        name = "wrong_%x.txt" % time.perf_counter_ns()
        path = ROOT / _REL / name
        path.write_text("something else entirely", encoding="utf-8")
        rel = "%s/%s" % (_REL, name)
        ok, reason, _evidence = acceptance.INSPECTORS["text.file.write"](
            {"content": "the text that was asked for", "output_path": rel},
            {"output_path": rel}, ROOT)
        self.assertIs(ok, False)
        self.assertIs(reason, "TEXT_OUTPUT_DOES_NOT_MATCH_THE_REQUESTED_TEXT")

    def test_a_file_that_is_not_there_is_refused(self) -> None:
        rel = "%s/absent_%x.txt" % (_REL, time.perf_counter_ns())
        ok, reason, _evidence = acceptance.INSPECTORS["text.file.write"](
            {"content": "anything", "output_path": rel}, {"output_path": rel}, ROOT)
        self.assertIs(ok, False)
        self.assertIs(reason, "TEXT_OUTPUT_ABSENT_FROM_DISK")

    def test_a_request_that_states_no_content_is_refused(self) -> None:
        # Nothing was asked for, so there is nothing to hold the bytes to.
        # Accepting here would be accepting an unchecked file.
        name = "nocontent_%x.txt" % time.perf_counter_ns()
        (ROOT / _REL / name).write_text("bytes", encoding="utf-8")
        rel = "%s/%s" % (_REL, name)
        ok, reason, _evidence = acceptance.INSPECTORS["text.file.write"](
            {"output_path": rel}, {"output_path": rel}, ROOT)
        self.assertIs(ok, False)
        self.assertIs(reason, "TEXT_REQUEST_STATES_NO_CONTENT_TO_CHECK")

    def test_a_file_that_matches_the_request_is_accepted(self) -> None:
        name = "right_%x.txt" % time.perf_counter_ns()
        text = "exactly what was asked for"
        (ROOT / _REL / name).write_text(text, encoding="utf-8")
        rel = "%s/%s" % (_REL, name)
        ok, reason, evidence = acceptance.INSPECTORS["text.file.write"](
            {"content": text, "output_path": rel}, {"output_path": rel}, ROOT)
        self.assertIs(ok, True, reason)
        self.assertIs(evidence.get("matches_the_requested_text"), True)
        self.assertEqual(evidence.get("bytes"), len(text.encode("utf-8")))

    # ---- end to end ------------------------------------------------------

    def test_a_natural_sentence_reaches_exact_semantic_acceptance(self) -> None:
        """The whole point.  On 83f1052 this returns PASS__COMPOSED_CAPABILITY_CHAIN."""
        rel = "%s/e2e.txt" % self._fresh_rel("e2e")
        # The CONTENT of the request is part of the sentence the router reads, so
        # the words chosen here are not free: "composed acceptance proof" was
        # measured to route to a chain through
        # python.software.request.semantic_behavior.compile.v1 instead of
        # text.file.write, because those words are that capability's tokens.
        # The wording below is the one measured to reach text.file.write.
        result = solve({"task_id": "COMPOSED_%x" % time.perf_counter_ns(),
                        "goal": "Write the text hello world to the file " + rel})
        self.assertIs(
            result.get("status"),
            "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED",
            "status=%s acceptance=%s" % (result.get("status"),
                                         result.get("raw_goal_acceptance")))
        self.assertIs(result.get("semantic_acceptance_complete"), True)
        self.assertTrue(result.get("accepted_raw_obligation_ids"),
                        "accepted no obligations")

    def test_the_verdict_is_bound_to_a_real_contract_and_real_evidence(self) -> None:
        """The acceptance must name a contract, obligations, and a re-inspection."""
        rel = "%s/ev.txt" % self._fresh_rel("ev")
        goal = "Write the text second proof to the file " + rel
        result = solve({"task_id": "COMPOSEDEV_%x" % time.perf_counter_ns(),
                        "goal": goal})
        acc = result.get("raw_goal_acceptance")
        self.assertIsInstance(acc, dict, "no acceptance verdict was recorded at all")
        self.assertIs(acc.get("status"), "RAW_GOAL_ACCEPTANCE_VERIFIED")
        self.assertIs(acc.get("pass"), True)
        # the verdict must be bound to THIS sentence, not to some other run
        self.assertEqual(acc.get("goal_sha256"),
                         hashlib.sha256(goal.encode("utf-8")).hexdigest())
        ledger = acc.get("reinspection_ledger") or acc.get("ledger") or []
        self.assertTrue(ledger, "acceptance recorded no re-inspection evidence")
        row = ledger[0]
        # assertEqual, not assertIs: these are equal strings from different
        # sources, and identity is not the claim being made.
        self.assertEqual(row.get("capability_id"), "text.file.write")
        self.assertIs((row.get("reinspection") or {}).get("file_reopened"), True)
        # and the file it accepted is really the text the sentence asked for
        self.assertEqual((ROOT / rel).read_text(encoding="utf-8"), "second proof")

    def test_a_chain_that_wrote_nothing_stays_provisional(self) -> None:
        """Negative control on the wiring: no effect, no acceptance."""
        from canonical.runtime.live_brain_route_admission_v1 import _composed_acceptance
        out = _composed_acceptance("Write the text x to the file " + _REL + "/none.txt",
                                   ["text.file.write"],
                                   {"steps": [{"index": 0,
                                               "capability_id": "text.file.write",
                                               "args": {"content": "x"},
                                               "result": {}}]})
        self.assertIs(out.get("semantic_acceptance_complete"), False)
        self.assertEqual(out.get("accepted_raw_obligation_ids"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
