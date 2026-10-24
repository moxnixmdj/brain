"""A composed step must record what the step actually produced.

`composer_route_v1.execute_chain` read a step's output as
`result.get("result")`.  But `run_adapter_locally` returns the adapter's own
dict AS the result -- `{"output_path": ..., "output_sha256": ...,
"output_verified": True, ...}` -- and never wraps it under a "result" key.  So
`observed` was None for every step of every chain, which had two consequences:

  * the step record was written as `{"raw": null}`, destroying the only
    evidence the step had produced;
  * `produced` stayed empty, so `bind` could never offer a later step anything
    an earlier step had made -- the mechanism multi-step composition exists for.

The chain still returned `pass: True`.  A composed goal therefore answered
"done" while its own record said nothing had been produced.  Nothing downstream
could verify it, because there was nothing to verify.

Measured on 2bd4c0b over six natural-language goals (the shape the composed path
exists for -- "Write the text X to the file Y", not an invocation naming a
capability): 5 of 6 passed, 4 took the composed chain, and

    BEFORE  step records carrying real evidence: 0 of 4   produced keys: 0
    AFTER   step records carrying real evidence: 4 of 4   produced keys: 24

Over all 367 admissible capabilities driven from prose: pass 223 / fail 144 and
failure kinds CONTRACT_REFUSAL 138 / ENVIRONMENT_BLOCKER 3 / UNKNOWN 3, all
unchanged, so no goal that routed before routes differently now.

The router emits only single-step chains for every goal measured, so the
cross-step consequence is not yet exercised in production; the evidence loss was
exercised on every composed execution there was.

Tests 1-3 drive the real composer and all fail on 2bd4c0b.  Test 4 is a
regression pin: the two keys `run_adapter_locally` stamps itself must not become
bindable slots for a later step.  Test 5 cross-checks the recorded evidence
against the bytes actually on disk, which is the point of recording it.
"""

from __future__ import annotations

import hashlib
import pathlib
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "canonical" / "runtime") not in sys.path:
    sys.path.insert(0, str(ROOT / "canonical" / "runtime"))

from canonical.runtime import composer_route_v1 as croute  # noqa: E402

_REL = "canonical/astra_runtime/tmp/composer_step_evidence_v1"


class TestAComposedStepRecordsWhatItProducedV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        (ROOT / _REL).mkdir(parents=True, exist_ok=True)

    def _run(self, tag: str) -> dict:
        # A unique path per run: the controller and the composer both remember
        # what they have already been asked, and a repeated request is not the
        # same measurement twice.
        name = "%s_%x.txt" % (tag, time.perf_counter_ns())
        goal = "Write the text composed step evidence to the file %s/%s" % (_REL, name)
        routed = croute.route(goal)
        self.assertTrue(routed.get("pass"), "router refused: %s" % routed.get("status"))
        executed = croute.execute_chain(routed["chain"], goal)
        executed["_path"] = "%s/%s" % (_REL, name)
        return executed

    def test_the_step_records_the_adapters_real_result(self) -> None:
        executed = self._run("real")
        self.assertIs(executed.get("status"), "PASS__COMPOSER_CHAIN_EXECUTED")
        steps = executed.get("steps") or []
        self.assertEqual(len(steps), 1)
        recorded = steps[0].get("result")
        self.assertNotEqual(recorded, {"raw": None},
                            "the step's evidence was destroyed")
        self.assertIsInstance(recorded, dict)
        self.assertIs(recorded.get("output_verified"), True)
        self.assertEqual(recorded.get("output_path"), executed["_path"])

    def test_produced_carries_what_the_step_made(self) -> None:
        executed = self._run("prod")
        produced = executed.get("produced") or {}
        self.assertIn("output_path", produced,
                      "a later step could never bind an earlier step's output")
        self.assertEqual(produced.get("output_path"), executed["_path"])
        self.assertIn("output_sha256", produced)

    def test_the_invokers_own_bookkeeping_is_not_an_output(self) -> None:
        # run_adapter_locally stamps these itself; they describe the invocation,
        # not what the capability produced, and must not become bindable slots.
        executed = self._run("stamp")
        produced = executed.get("produced") or {}
        for key in ("capability_id", "dependency"):
            self.assertNotIn(key, produced)

    def test_the_recorded_evidence_matches_the_bytes_on_disk(self) -> None:
        """The reason to record evidence is that it can be checked."""
        executed = self._run("disk")
        produced = executed.get("produced") or {}
        path = ROOT / produced["output_path"]
        self.assertTrue(path.is_file(), "recorded an output that is not on disk")
        blob = path.read_bytes()
        self.assertEqual(len(blob), produced.get("output_bytes"))
        self.assertEqual(hashlib.sha256(blob).hexdigest(),
                         produced.get("output_sha256"))
        self.assertEqual(blob.decode("utf-8"), "composed step evidence")

    def test_a_step_that_fails_still_fails_the_chain(self) -> None:
        # Negative control: recording more must not make a failure look like a
        # success.  A capability that is not in the registry fails closed.
        out = croute.execute_chain(["no.such.capability.v1"], "irrelevant")
        self.assertIs(out.get("pass"), False)
        self.assertIs(out.get("status"), "FAIL__COMPOSER_STEP_NOT_IN_REGISTRY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
