from __future__ import annotations
import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Tests(unittest.TestCase):
    def test_activation_is_narrow_zero_credit_and_pre_reality(self):
        v=load("canonical/verification/DIFFERENTIAL_DOMINANCE_COMPILER_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        a=load("canonical/governance/DIFFERENTIAL_DOMINANCE_COMPILER_ACTIVATION_V1.json")
        o=load("canonical/governance/EXECUTION_FIRST_SELF_PROVING_OPTIMIZER_V1.json")
        h=load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")
        n=load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V1.json")
        self.assertTrue(v["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"))
        self.assertEqual(v["public_runner"]["conclusion"],"success")
        self.assertFalse(a["promotion_authority"]); self.assertEqual(a["new_reality_units_consumed"],0)
        self.assertIn("INDEPENDENT_VERIFICATION_REQUIRED", n["status"])
        step="FINITE_DIFFERENTIAL_DOMINANCE_ELIMINATION"
        self.assertLess(o["execution_ladder"].index(step),o["execution_ladder"].index("EXACT_MINIMUM_REALITY_CUT"))
        action=next(x for x in h["actions"] if x["id"]=="RUN_FINITE_DIFFERENTIAL_DOMINANCE_ELIMINATION")
        # This used to pin the six-predicate set literally. Three of those six
        # have since been proved, and a proved predicate is no longer remaining
        # work, so the open-predicate guard now requires the frontier to drop
        # them. Deriving the expectation from the evidence bindings keeps the
        # intent -- this action targets exactly this activation set and nothing
        # wider -- without going red every time one of them is discharged.
        ev=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        proved={c["predicate_id"] for c in ev["claims"] if c.get("state")=="PROVED"}
        documented={"AGENCY_MATCHED_SUCCESS_NONINFERIOR","IF_SCOPE_BOUNDARY_NONINFERIOR","RECOVERY_TERMINAL_NONINFERIOR","RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR","SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR","COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR"}
        self.assertTrue(proved & documented, "fixture drifted: no documented target has been proved")
        self.assertEqual(set(action["target_predicates"]),documented-proved)
        # This used to assert that the normalization precondition was still
        # unsatisfied. It has since been independently verified, so pinning
        # False was stale. What the test actually needs -- and what the action's
        # own notes promise -- is narrower and durable: a precondition may only
        # be called satisfied if it names independent evidence that exists, and
        # the step must remain blocked, because "no cases may be generated
        # merely to satisfy this precondition".
        for p in action["preconditions"]:
            if p["satisfied"]:
                self.assertTrue(p.get("evidence"),f"{p['id']} marked satisfied with no evidence path")
                self.assertTrue((ROOT/p["evidence"]).exists(),f"evidence missing for satisfied precondition {p['id']}: {p['evidence']}")
        self.assertTrue(
            any(not p["satisfied"] for p in action["preconditions"]),
            "differential dominance is no longer blocked by any precondition",
        )
        forbidden={"DELEGATION_TERMINAL_SUCCESS_NONINFERIOR","TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR","CODING_TB4_GE_66_4","AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION","IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS","RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES","COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES"}
        self.assertFalse(set(action["target_predicates"]) & forbidden)
if __name__=="__main__": unittest.main(verbosity=2)
