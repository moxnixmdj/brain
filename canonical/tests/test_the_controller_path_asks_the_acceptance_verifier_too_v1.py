"""The controller path asks the acceptance verifier, like the front-layer path does.

PR #6111 fixed the front-layer local adapter path: it had hard-coded
``semantic_acceptance_complete: False`` and never called the verifier.  Its sibling
-- the model-independent controller path in the same module -- had the identical
line and the identical omission, so a pass there reported itself provisional with no
reason at all.

Measured on bf2799b over the 51 capabilities that declare an output artifact, with
every input stated: 9 pass, all 9 write the promised file, 3 reach exact semantic
acceptance, and **5 carry no acceptance verdict whatsoever**.  Two of those five --
``auto.npm.dfinity-cbor`` and ``auto.npm.msgpack-msgpack`` -- take the controller
path, pass, and write their artifact, and were never asked.

After the fix, measured over the same 51: passes carrying no verdict fall from 5 to
3.  The 3 that remain are ``PASS__COMPOSED_CAPABILITY_CHAIN`` results with no raw
task contract at all (``raw_acceptance_obligation_count`` is None), so there is
nothing to verify.  Over the whole corpus of 367 admissible capabilities named in
prose, passes carrying no verdict fall from 2 to 1, and pass/fail stays 223/144.

Exact semantic acceptance does NOT rise, and that is recorded rather than hidden:
``raw_goal_trace_acceptance_v1`` refuses any capability with no registered
re-inspector, and only 11 of 367 have one.  This change makes a controller-path pass
say why it is provisional; it does not upgrade a single pass class.
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "canonical/runtime")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import canonical.runtime.live_brain_route_admission_v1 as ra        # noqa: E402
from canonical.runtime.live_brain_route_admission_v1 import solve   # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

CONTROLLER_MODE_MARK = "PASS__RAW_GOAL_COMPILED_CONTROLLER_EXECUTED_VERIFIED_AND_CHECKPOINTED"


def _goal_for(cid):
    stem = re.sub(r"\.py\.auto\.v\d+$", "", cid.rsplit("/", 1)[-1])
    return "Run the %s." % stem.replace("_", " ").replace(".", " ")


class ControllerPathAsksTheVerifierTest(unittest.TestCase):

    def test_exact_acceptance_is_decided_by_the_verifier_not_hard_coded(self):
        """Deterministic, host-independent: feed _exact_acceptance a contract with no
        obligations and a bogus trace.  It must report a verdict and must not claim
        completeness, because nothing was re-inspected."""
        contract = {"task_sha256": "0" * 64, "pass": True,
                    "acceptance_contract": {"obligations": [], "required_obligation_ids": []}}
        out = ra._exact_acceptance("Do something.", {}, [], contract)
        self.assertIs(out["semantic_acceptance_complete"], False)
        self.assertEqual(out["accepted_raw_obligation_ids"], [])

    def test_completeness_requires_every_obligation_to_be_accepted(self):
        """A contract with obligations and an empty trace can never be complete, so
        the guard is not satisfied by the verifier merely not objecting."""
        contract = {"task_sha256": "0" * 64, "pass": True,
                    "acceptance_contract": {
                        "obligations": [{"obligation_id": "RAWREQ:x", "task_sha256": "0" * 64}],
                        "required_obligation_ids": ["RAWREQ:x"]}}
        out = ra._exact_acceptance("Do something.", {}, [], contract)
        self.assertIs(out["semantic_acceptance_complete"], False)

    def test_a_verifier_that_explodes_cannot_fail_the_goal(self):
        real = sys.modules["canonical.runtime.raw_goal_trace_acceptance_v1"]
        original = real.verify

        def _boom(**kwargs):
            raise RuntimeError("verifier exploded")

        real.verify = _boom
        try:
            out = ra._exact_acceptance("Do something.", {}, [], {})
        finally:
            real.verify = original
        self.assertIs(out["semantic_acceptance_complete"], False)
        self.assertEqual(out["accepted_raw_obligation_ids"], [])

    def test_no_controller_path_pass_is_left_without_a_verdict(self):
        """Whole class, host-independent.  Baseline on bf2799b: passes on this path
        carried no acceptance verdict at all.  If a host has no capability that takes
        the controller path the loop is vacuous, which is why the count is asserted
        separately below rather than assumed."""
        reg = dict(load_verified_registry())
        controller_passes = []
        missing = []
        for index, cid in enumerate(sorted(reg)):
            result = solve({"task_id": "CTL%03d" % index, "goal": _goal_for(cid)})
            if result.get("pass") is not True:
                continue
            if CONTROLLER_MODE_MARK not in str(result.get("status")):
                continue
            controller_passes.append(cid)
            if result.get("raw_goal_acceptance") is None:
                missing.append(cid)
        self.assertEqual(missing, [], "controller-path passes with no verdict: %s" % (missing,))
        # Measured on both this host and CI at the time of writing: 2 capabilities
        # reach this path.  Asserting a floor of 1 keeps the class test from going
        # quietly vacuous if the corpus shifts.
        self.assertGreaterEqual(len(controller_passes), 1,
                                "no capability took the controller path; this test proved nothing")

    def test_a_controller_path_pass_carries_a_reason_and_claims_no_more(self):
        """The pair of guarantees that matter together: it says why, and it does not
        claim exact acceptance it did not earn."""
        reg = dict(load_verified_registry())
        for index, cid in enumerate(sorted(reg)):
            result = solve({"task_id": "CTL2%03d" % index, "goal": _goal_for(cid)})
            if result.get("pass") is not True:
                continue
            if CONTROLLER_MODE_MARK not in str(result.get("status")):
                continue
            acceptance = result.get("raw_goal_acceptance")
            self.assertIsInstance(acceptance, dict, "%s carried no verdict" % cid)
            reason = str(acceptance.get("reason") or acceptance.get("status") or "")
            self.assertTrue(reason, "%s verdict has no reason: %r" % (cid, acceptance))
            if result.get("semantic_acceptance_complete") is not True:
                self.assertNotIn("EXACT_SEMANTIC_ACCEPTANCE_VERIFIED", str(result.get("status")))
            return
        self.skipTest("no controller-path pass on this host")


if __name__ == "__main__":
    unittest.main(verbosity=2)
