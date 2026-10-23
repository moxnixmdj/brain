#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH=ROOT/"runtime"/"astra_runtime.py"
spec=importlib.util.spec_from_file_location("project_brain_grounding_bound_integration",RUNTIME_PATH)
runtime=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=runtime
spec.loader.exec_module(runtime)

class PlainGoalGroundingBoundIntegrationTests(unittest.TestCase):
    def test_registry_producer_and_independent_verifier_are_callable(self):
        registry=json.loads(
            (ROOT/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8")
        )["capabilities"]
        producer="plain_goal.bound_capability.grounding.stdlib"
        verifier="plain_goal.bound_capability.grounding.verify.stdlib"
        self.assertEqual(registry[producer]["status"],"VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(registry[verifier]["status"],"VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(registry[producer]["verification"]["model_dependency_count"],0)
        self.assertEqual(registry[verifier]["verification"]["model_dependency_count"],0)

        goal="Audit the Python tests with unittest and report passed failed and skipped counts."
        rel="canonical/astra_runtime/tmp/BOUND_GROUNDING_REGISTRY_INTEGRATION.json"
        path=pathlib.Path.cwd()/rel
        path.unlink(missing_ok=True)
        self.addCleanup(lambda:path.unlink(missing_ok=True))

        produced=runtime._goal_action({
            "type":"invoke_capability",
            "args":{
                "capability_id":producer,
                "goal":goal,
                "output_path":rel,
            },
        })
        self.assertTrue(produced["output_verified"],produced)
        self.assertEqual(produced["model_dependency_count"],0)
        # What this report must say, and why it says it.
        #
        # It used to assert that python.tests.audit.unittest appeared in
        # candidate_capability_ids.  That contradicts a design decision this repository
        # pins in three places at once, so the assertion was the thing out of step, not
        # the runtime:
        #
        #   * canonical/tests/test_brain_unified_model_v1.py pins never_emitted =
        #     {"GROUNDED","AMBIGUOUS_BOUNDED"} across every benchmark goal, with the
        #     load-bearing claim ok == (grounded_clause_count == 0) and the measured
        #     split frozen at (16 passed, 7 failed).  A green grounding verification
        #     certifies EMPTINESS, not success.
        #   * The same file's docstring states that widening the verifier to accept
        #     UNBOUND_INPUTS_NOT_GROUNDED "would invalidate the ACQUIRED_VERIFIED
        #     receipt that pins this adapter's git blob byte-for-byte ... which is why
        #     the gap is pinned rather than closed here."
        #   * test_the_grounding_verifier_adapter_still_matches_its_acquisition_receipt
        #     pins the adapter's bytes to that receipt, so the widening cannot happen
        #     silently.
        #
        # Forcing the audit capability to bind also needs a `pattern` and a `source_root`
        # that this sentence never states, so satisfying the old assertion meant inventing
        # a glob - and making report writers bindable at all was measured to drop
        # expected_first_selected from 22 of 23 to 12 of 23.  Both routes encode a guess.
        report=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(report["clauses"][0]["status"],"UNRESOLVED")
        self.assertEqual(report["clauses"][0]["candidates"],[])
        self.assertEqual(report["grounded_clause_count"],0)
        self.assertEqual(report["unresolved_clause_indexes"],[0])
        self.assertEqual(produced["candidate_capability_ids"],[])

        verified=runtime._goal_action({
            "type":"invoke_capability",
            "args":{
                "capability_id":verifier,
                "goal":goal,
                "result_path":rel,
            },
        })
        self.assertTrue(verified["verified"],verified)
        self.assertTrue(verified["producer_independent"])
        self.assertEqual(verified["model_dependency_count"],0)

    def test_the_verifiers_green_check_certifies_emptiness_not_success(self):
        """A passing grounding verification means NOTHING WAS GROUNDED.

        That is the opposite of what a green check looks like from outside, so it is pinned
        on its own: a report that claims a grounded clause must be REJECTED by the same
        verifier that accepted the empty one.  Without this, "verified: true" could silently
        come to mean "the producer says it worked".

        Measured, two independent checks reject the claim, and each is sufficient alone:
        neutering GROUNDED_CARDINALITY_INVALID leaves GROUNDED_COUNT_MISMATCH to catch it,
        and neutering that leaves the cardinality rule.  So this pins the CONTRACT - a claim
        of grounding that the report's own contents contradict is refused - not either rule
        in isolation.  A claim that is internally consistent (one GROUNDED clause, exactly
        one candidate, count 1) is NOT caught here, because catching that needs re-deriving
        the grounding from the goal, which this verifier does not do and does not claim to.
        """
        goal="Audit the Python tests with unittest and report passed failed and skipped counts."
        rel="canonical/astra_runtime/tmp/BOUND_GROUNDING_HONESTY_PROBE.json"
        path=pathlib.Path.cwd()/rel
        path.unlink(missing_ok=True)
        self.addCleanup(lambda:path.unlink(missing_ok=True))

        runtime._goal_action({
            "type":"invoke_capability",
            "args":{
                "capability_id":"plain_goal.bound_capability.grounding.stdlib",
                "goal":goal,
                "output_path":rel,
            },
        })
        honest=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(honest["grounded_clause_count"],0,honest["unresolved_clause_indexes"])

        checked=runtime._goal_action({
            "type":"invoke_capability",
            "args":{
                "capability_id":"plain_goal.bound_capability.grounding.verify.stdlib",
                "goal":goal,
                "result_path":rel,
            },
        })
        self.assertTrue(checked["verified"],checked)

        # Now lie to the verifier in the smallest possible way: claim the clause grounded.
        lied=dict(honest)
        lied["grounded_clause_count"]=1
        lied["clauses"]=[dict(honest["clauses"][0],status="GROUNDED")]
        path.write_text(json.dumps(lied,indent=2,sort_keys=True)+"\n",encoding="utf-8")

        rejected=runtime._goal_action({
            "type":"invoke_capability",
            "args":{
                "capability_id":"plain_goal.bound_capability.grounding.verify.stdlib",
                "goal":goal,
                "result_path":rel,
            },
        })
        self.assertFalse(rejected["verified"],
                         "the verifier accepted a report claiming a grounded clause: %s"%(rejected,))
        self.assertIn(str(rejected.get("reason")),
                      ("GROUNDED_CARDINALITY_INVALID","GROUNDED_COUNT_MISMATCH"),
                      rejected)

if __name__=="__main__":
    unittest.main(verbosity=2)
