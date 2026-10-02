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
        expected={"AGENCY_MATCHED_SUCCESS_NONINFERIOR","IF_SCOPE_BOUNDARY_NONINFERIOR","RECOVERY_TERMINAL_NONINFERIOR","RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR","SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR","COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR"}
        self.assertEqual(set(action["target_predicates"]),expected)
        norm=next(p for p in action["preconditions"] if p["id"]=="MATCHED_TARGET_NORMALIZATION_INDEPENDENT_PASS")
        self.assertFalse(norm["satisfied"])
        forbidden={"DELEGATION_TERMINAL_SUCCESS_NONINFERIOR","TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR","CODING_TB4_GE_66_4","AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION","IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS","RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES","COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES"}
        self.assertFalse(set(action["target_predicates"]) & forbidden)
if __name__=="__main__": unittest.main(verbosity=2)
