from __future__ import annotations
import json, unittest
from pathlib import Path
from canonical.runtime.adaptive_terminal_closure_controller_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

class AdaptiveControllerTests(unittest.TestCase):
    def docs(self):
        return (
            load("canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json"),
            load("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"),
            load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"),
            load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        )

    def test_live(self):
        out=evaluate(*self.docs())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["live_world"]["unresolved_predicates"],27)
        self.assertEqual(out["live_world"]["nondominated_certificates"],16)
        self.assertEqual(out["live_world"]["unique_zero_reality_requirements"],19)
        self.assertEqual(out["live_world"]["matched_primitive_child_facts"],16)
        self.assertEqual(out["live_world"]["other_zero_reality_requirements"],17)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])

    def test_no_probability_invented(self):
        out=evaluate(*self.docs())
        self.assertTrue(all(
            x["probability"]["status"]=="UNKNOWN_NOT_INVENTED"
            for x in out["other_zero_reality_batch"]
        ))

    def test_special_pruning(self):
        out=evaluate(*self.docs())
        by={x["requirement_id"]:x for x in out["other_zero_reality_batch"]}
        self.assertEqual(
            by["MACHINE_VERIFIED_TB4_ROUTE_UPPER_BOUND_GE_220"]["execution_mode"],
            "ROUTE_SEARCH_ONLY",
        )
        tool=[x for x in by.values() if x["requirement_id"].endswith("TOOL_DISCOVERY_PROTOCOL")][0]
        self.assertEqual(tool["execution_mode"],"NEW_SOURCE_EPOCH_OR_SCOPE_PROOF_ONLY")

    def test_ownership_runs_in_parallel(self):
        out=evaluate(*self.docs())
        fam={x["family"] for x in out["ownership_reconciliation_batch"]}
        self.assertIn("SUBAGENT_DELEGATION_AND_COORDINATION",fam)
        self.assertIn("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",fam)
        self.assertNotIn("EXACT_SYMBOLIC_COMPUTATION",fam)
        self.assertNotIn("LONG_HORIZON_MEMORY_AND_CONTINUITY",fam)

    def test_explicit_probability_input_only(self):
        req="GDPVAL_AA_ROUTE_BOUND"
        empirical={req:{
            "prior_alpha":1,"prior_beta":1,"successes":3,"failures":1,
            "mean_latency_seconds":20,
        }}
        out=evaluate(*self.docs(),empirical)
        row=next(x for x in out["other_zero_reality_batch"] if x["requirement_id"]==req)
        self.assertEqual(row["probability"]["status"],"EMPIRICAL_BETA_POSTERIOR")
        self.assertAlmostEqual(row["probability"]["posterior_mean"],4/6)
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__": unittest.main(verbosity=2)
